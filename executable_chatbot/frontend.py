import streamlit as st 
from langchain_core.messages import BaseMessage , HumanMessage
from backend import chatbot

CONFG = {'configurable':{"thread_id":"thread-1"}}

if "messages" not in st.session_state:
    st.session_state['messages'] = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['message'])


user_input = st.chat_input("Type here ")

if user_input:

    

    st.session_state.messages.append({'role':"user" , "message":user_input})

    with st.chat_message("user"):
        st.write(user_input)
    with st.spinner("Genrating answer"):

        AI_res = chatbot.invoke({'messages':[HumanMessage(content=user_input)]} , config=CONFG)

    AI_message = AI_res['messages'][-1].content

    

    st.session_state.messages.append({"role":"assistant" , "message":AI_message})

    st.rerun()