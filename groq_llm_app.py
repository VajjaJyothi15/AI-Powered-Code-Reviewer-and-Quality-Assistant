import os

import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage


def render_groq_llm_playground() -> None:
    """Render the Groq LLM playground UI."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    st.subheader("🤖 Groq LLM Playground")

    if not api_key:
        st.error("GROQ_API_KEY not found. Please set it in your .env file.")
        return

    model_name = st.selectbox(
        "LLM Model",
        ["openai/gpt-oss-120b", "llama-3.1-8b-instant"],
        index=0,
        key="groq_model_select",
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05, key="groq_temp")

    user_input = st.text_area(
        "Enter your prompt:",
        value="What is a data scientist? Explain step by step.",
        key="groq_prompt",
    )

    if st.button("Run LLM", key="groq_run"):
        if not user_input.strip():
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("Thinking..."):
                llm = ChatGroq(
                    model=model_name,
                    temperature=temperature,
                    api_key=api_key,
                )
                response = llm.invoke([HumanMessage(content=user_input)])

            st.subheader("Response:")
            st.write(response.content)


if __name__ == "__main__":
    st.title("Groq LLM Test (LangChain + Streamlit)")
    render_groq_llm_playground()
