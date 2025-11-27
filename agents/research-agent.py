import streamlit as st
import google.generativeai as genai
import requests
import os

# --- Constants ---
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_PAPERS_TO_SUMMARIZE = 3  # Limit the number of papers to process to avoid excessive API calls/time

# --- Helper Functions ---

def search_semantic_scholar(query: str, limit: int = MAX_PAPERS_TO_SUMMARIZE):
    """
    Searches Semantic Scholar for research papers based on a query.
    Returns a list of dictionaries with paper details (title, abstract, url, authors).
    """
    params = {
        "query": query,
        "fields": "title,abstract,url,authors",  # Request necessary fields
        "limit": limit
    }
    headers = {
        # It's good practice to identify your application in the User-Agent header
        "User-Agent": "StreamlitGeminiPaperSummarizer/1.0 (contact@example.com)"
    }
    try:
        response = requests.get(SEMANTIC_SCHOLAR_API_URL, params=params, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if data and 'data' in data:
            papers = []
            for item in data['data']:
                papers.append({
                    "title": item.get("title", "No Title Available"),
                    "abstract": item.get("abstract", "No Abstract Available."),
                    "url": item.get("url", "#"),
                    "authors": ", ".join([a['name'] for a in item.get('authors', [])])
                })
            return papers
        else:
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error searching Semantic Scholar: {e}")
        return []

def get_gemini_summary(api_key: str, paper_abstract: str):
    """
    Generates a concise summary of a paper abstract using Google Gemini.
    """
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        # Using gemini-1.5-flash as it's good for summarization and cost-effective
        client = genai.GenerativeModel("gemini-2.5-flash")

        # Craft a specific prompt for summarization
        prompt = f"""Summarize the following research paper abstract concisely in 3-4 sentences.
        Focus on the main objective, methodology, key findings, and conclusion.

        Abstract:
        {paper_abstract}

        Summary:
        """
        response = client.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating summary with Gemini: {e}")
        return None

# --- Streamlit App ---

st.set_page_config(page_title="Gemini Research Paper Summarizer", layout="wide")

st.title("🔬 Research Paper Summarizer")
st.markdown("""
This app helps you find relevant research papers based on your abstract input and summarizes them using Google Gemini.
**Important Note:** Due to limitations in programmatically accessing and parsing full paper content, the summaries are
generated based on the *abstracts* of the found papers, not their full text.
""")

# --- 1. Gemini API Key Input ---
st.header("1. Enter Your Gemini API Key")
gemini_api_key = st.text_input(
    "Google Gemini API Key",
    type="password",
    help="You can get your API key from https://makersuite.google.com/keys. For production apps, consider using `st.secrets`."
)

if not gemini_api_key:
    st.warning("Please enter your Gemini API Key to proceed.")

# --- 2. User Abstract Input ---
st.header("2. Input Your Research Abstract")
user_abstract = st.text_area(
    "Paste your research abstract here:",
    height=200,
    placeholder="Example: This paper proposes a novel deep learning architecture for image classification on medical datasets. We evaluate our model on X-ray images, achieving state-of-the-art performance with significantly reduced computational cost compared to existing methods. Our findings suggest that tailored architectures can outperform general-purpose models for specialized tasks..."
)

# --- 3. Process Button ---
# Disable button if API key or abstract is missing
button_disabled = not (gemini_api_key and user_abstract)

if st.button("Find Papers and Summarize", disabled=button_disabled):
    if not gemini_api_key:
        st.error("Please enter your Gemini API Key.")
    elif not user_abstract:
        st.error("Please enter your abstract to search for papers.")
    else:
        st.header("3. Search Results and Summaries")
        with st.spinner(f"Searching for up to {MAX_PAPERS_TO_SUMMARIZE} relevant papers and generating summaries... This might take a moment."):
            # Step 1: Search for papers using Semantic Scholar
            st.subheader("Searching Semantic Scholar...")
            found_papers = search_semantic_scholar(user_abstract, limit=MAX_PAPERS_TO_SUMMARIZE)

            if not found_papers:
                st.info("No relevant papers found on Semantic Scholar based on your abstract. Try refining your input.")
            else:
                st.success(f"Found {len(found_papers)} relevant papers. Generating summaries...")

                for i, paper in enumerate(found_papers):
                    st.markdown(f"---")
                    st.subheader(f"Paper {i+1}: {paper['title']}")
                    st.markdown(f"**Authors:** {paper['authors']}")
                    st.markdown(f"**Abstract:** {paper['abstract']}")
                    st.markdown(f"**Link:** [Read on Semantic Scholar]({paper['url']})")

                    # Step 2: Summarize each paper's abstract using Gemini
                    summary = get_gemini_summary(gemini_api_key, paper['abstract'])

                    if summary:
                        st.markdown(f"**Gemini Summary:**")
                        st.info(summary)
                    else:
                        st.warning("Could not generate a summary for this paper using Gemini.")

st.markdown("---")
st.caption("Powered by Google Gemini and Semantic Scholar API.")