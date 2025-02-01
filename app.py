import torch
import ollama
import os
from openai import OpenAI
import argparse
import streamlit as st

# Set flag to see more intermittent steps
DEBUG = False

st.title("Monopoly Bot")

with st.chat_message("assistant"):
    st.write("Hello 👋, I'm here to answer questions about the game called Monopoly.")

# Function to open a file and return its contents as a string
def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

# Function to get relevant context from the vault based on user input
def get_relevant_context(rewritten_input, vault_embeddings, vault_content, top_k=3):
    if vault_embeddings.nelement() == 0:  # Check if the tensor has any elements
        return []
    
    # Encode the rewritten input
    input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=rewritten_input)["embedding"]
    # You can try another embedding model
    # input_embedding = ollama.embeddings(model='nomic-embed-text', prompt=rewritten_input)["embedding"]

    # Compute cosine similarity between the input and vault embeddings
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)

    # Adjust top_k if it's greater than the number of available scores
    top_k = min(top_k, len(cos_scores))

    # Sort the scores and get the top-k indices
    top_indices = torch.topk(cos_scores, k=top_k)[1].tolist()

    # Get the corresponding context from the vault
    relevant_context = [vault_content[idx].strip() for idx in top_indices]
    return relevant_context

# Function to interact with the Ollama model
def ollama_chat(user_input, system_message, vault_embeddings, vault_content, ollama_model, conversation_history):
    # Get relevant context from the vault
    relevant_context = get_relevant_context(user_input, vault_embeddings_tensor, vault_content, top_k=3)
    if relevant_context:
        # Convert list to a single string with newlines between items
        context_str = "\n".join(relevant_context)
        if DEBUG == True:
            print("Context Pulled from Documents: \n\n")
    else:
        if DEBUG == True:
            print("No relevant context found.")
    
    # Prepare the user's input by concatenating it with the relevant context
    user_input_with_context = user_input
    if relevant_context:
        user_input_with_context = context_str + "\n\n" + user_input
    
    # Append the user's input to the conversation history
    conversation_history.append({"role": "user", "content": user_input_with_context})
    
    # Create a message history including the system message and the conversation history
    messages = [
        {"role": "system", "content": system_message},
        *conversation_history
    ]
    
    # Send the completion request to the Ollama model
    response = client.chat.completions.create(
        model=ollama_model,
        messages=messages
    )
    
    # Append the model's response to the conversation history
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})
    
    # Return the content of the response from the model
    return response.choices[0].message.content

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Ollama Chat")
parser.add_argument("--model", default="dolphin-llama3", help="Ollama model to use (default: llama3)")
args = parser.parse_args()

# Configuration for the Ollama API client
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='dolphin-llama3'
)

# Load the vault content
vault_content = []
if os.path.exists("annie_monopoly_vault.txt"):
    with open("annie_monopoly_vault.txt", "r", encoding='utf-8') as vault_file:
        vault_content = vault_file.readlines()

# Generate embeddings for the vault content using Ollama
vault_embeddings = []
for content in vault_content:
    # You need to use the same embedding model for the prompt as you did with the vault
    response = ollama.embeddings(model='mxbai-embed-large', prompt=content)
    # You can try another embedding model
    # response = ollama.embeddings(model='nomic-embed-text', prompt=content)

    vault_embeddings.append(response["embedding"])

# Convert to tensor and print embeddings
vault_embeddings_tensor = torch.tensor(vault_embeddings) 

if DEBUG == True:
    print("Embeddings for each line in the vault:")
    print(vault_embeddings_tensor)

# Conversation loop
conversation_history = []

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# You can enter a very specific prompt to the AI chatbot to guide it to talk only about a specific topic
system_message = "You are a helpful assistant to answer only questions regarding the \
    Monopoly game provided in the given document. If a player is referring to a game, \
    assume they are referring to the Monopoly game. For other questions not related to the game, \
    simply apologize saying that I cannot answer questions not related to the Monopoly game."

# React to user input
if prompt := st.chat_input("Enter your question"):
    # Display user message in chat message container
    st.chat_message("user").markdown(
            """
            <style>
                .st-emotion-cache-janbn0 {
                    flex-direction: row-reverse;
                    text-align: right;
                } 
            </style>
            %s
            """ % prompt,
            unsafe_allow_html=True,
        )

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Find answer from Ollama
    response = ollama_chat(prompt, system_message, vault_embeddings_tensor, vault_content, args.model, conversation_history)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown( 
            """
            <style>
                .st-emotion-cache-janbn0 {
                    flex-direction: row-reverse;
                    text-align: right;
                } 
            </style>
            %s
            """ % response,
        unsafe_allow_html=True,
        )

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})