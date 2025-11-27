import streamlit as st
import google.generativeai as genai

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="Text Sentiment Analyzer with Gemini",
    layout="centered",
    initial_sidebar_state="auto"
)

st.title("✨ Gemini-Powered Sentiment Analyzer")
st.markdown("Analyze the sentiment (Positive, Negative, or Neutral) of your text using Google's `gemini-2.5-flash` AI model.")
st.markdown("---")

# --- Gemini API Key Input ---
# The user-supplied key is stored in the placeholder variable USER_GEMINI_KEY as requested.
USER_GEMINI_KEY = st.text_input(
    "🔑 Enter your Gemini API Key",
    type="password", # Mask the input for security
    help="You can obtain a Gemini API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)"
)

st.markdown("---")

# --- Text Input for Analysis ---
user_text = st.text_area(
    "✍️ Enter the text you want to analyze:",
    height=200,
    placeholder="Example: 'I absolutely love this new feature, it's fantastic and works perfectly!'",
    help="Type or paste the text for sentiment analysis here. The model will determine if it's Positive, Negative, or Neutral."
)

st.markdown("---")

# --- Sentiment Analysis Button and Logic ---
if st.button("Analyze Sentiment", use_container_width=True, type="primary"):
    if not USER_GEMINI_KEY:
        st.error("🚨 Please enter your Gemini API Key to proceed with the analysis.")
    elif not user_text:
        st.warning("⚠️ Please enter some text in the text area to analyze its sentiment.")
    else:
        try:
            # Configure the genai client with the user-supplied API key.
            # As per the example: client = genai.Client(api_key=user_supplied_key)
            # In the `google-generativeai` library, this pattern is achieved by:
            # 1. Configuring the API key globally.
            genai.configure(api_key=USER_GEMINI_KEY)
            # 2. Obtaining a client object that has the `models` attribute for content generation.
            client = genai.get_client() 

            # Define the prompt for sentiment analysis.
            # We instruct the model to provide a very specific, single-word output
            # for easy and consistent parsing.
            prompt = f"""
            Analyze the sentiment of the following text.
            Respond with *only one word*: 'Positive', 'Negative', or 'Neutral'.
            Do not include any other text, explanation, punctuation, or formatting.

            Text:
            "{user_text}"
            """
            
            # Make the API call to the specified Gemini model.
            # As per the example: response = client.models.generate_content(model="gemini-2.5-flash", contents="Hello")
            with st.spinner("🚀 Analyzing sentiment using Gemini..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash", # Using the model specified in requirements
                    contents=[prompt]
                )

            # --- Extract and Display Sentiment ---
            if response and response.candidates:
                # Get the first part of the content from the first candidate.
                # The model's response should be just "Positive", "Negative", or "Neutral".
                sentiment_raw = response.candidates[0].content.parts[0].text.strip()
                sentiment = sentiment_raw.upper() # Standardize to uppercase for reliable comparison

                st.subheader("Results:")
                if "POSITIVE" in sentiment:
                    st.success(f"**Sentiment: Positive** 😃")
                elif "NEGATIVE" in sentiment:
                    st.error(f"**Sentiment: Negative** 😠")
                elif "NEUTRAL" in sentiment:
                    st.info(f"**Sentiment: Neutral** 😐")
                else:
                    st.warning(f"🤔 Could not determine a clear sentiment. Gemini's response was: '{sentiment_raw}'.")
                    # Optional: Show full raw response for debugging purposes if the output wasn't as expected.
                    with st.expander("Show full Gemini API response"):
                        st.json(response.to_dict())
            else:
                st.error("❌ No valid response received from the Gemini model. It might have refused to generate content based on safety policies or other issues.")
                # If there's a response object but no candidates, it might contain error information.
                if response:
                    with st.expander("Show raw API response (if available)"):
                        st.json(response.to_dict())

        except Exception as e:
            st.error(f"❌ An error occurred during analysis: {e}")
            st.warning("Please check the following:")
            st.markdown("- **Your Gemini API key** might be incorrect, invalid, or expired.")
            st.markdown("- **Network connectivity** issues.")
            st.markdown("- The **content of your text** might violate Gemini's safety policies, causing the model to block a response.")

st.markdown("---")
st.caption("Built with Streamlit and Google Gemini API.")