import streamlit as st 
from langchain_core.messages import  HumanMessage
from backend import chatbot , model ,save_threads , get_threads_data
import uuid

# ------------------------------------------------------ utility functions---------------------------------------------
def genrate_thread():
    thread = uuid.uuid4()
    
    return thread



def load_chat(thread_id):
    temp_list = []
    output = chatbot.get_state({'configurable':{"thread_id":thread_id}})
    messages = output.values['messages']
    for msg in messages:
        if isinstance(msg , HumanMessage):
            role = "user"
        else:
            role="assistant"
        temp_list.append({"role":role , "message":msg.content})
    st.session_state['messages'] = temp_list
    st.session_state['thread_id']=thread_id
    st.rerun()

# def save_thread_titles(thread_id,title):
#     if thread_id not in [item['thread_id'] for item in st.session_state['thread_naming']]:
#             st.session_state['thread_naming'].append({"thread_id":thread_id , "title":title})





def genrate_thread_titles(thread_id):
   
    temp_list = []
    output = chatbot.get_state({'configurable':{"thread_id":thread_id}})
    
    messages = output.values.get('messages',[])
    
    if messages is None:
        return "New Chat"
    for msg in messages:
        if isinstance(msg , HumanMessage):
                role = "user"
        else:
                role="assistant"
        temp_list.append({"role":role , "message":msg.content})
    
    res = model.invoke(f"""
        Give me a short title for this conversation.

        Requirements:
        - Minimum 2 words
        - Maximum 5 words
        - No quotation marks

        Conversation:
        {temp_list}
        """)
    
    
    return res.content






# -------------------------------state tools management-----------------------------------------------------------------


if 'thread_naming' not in st.session_state:
    st.session_state['thread_naming']=get_threads_data()  # backend function 




if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = genrate_thread()


if "messages" not in st.session_state:
    st.session_state['messages'] = []



# ----------------------------------------------------sidebar panel------------------------------------------------
st.sidebar.title("Your chats")

if st.sidebar.button("New chat"):
    new_thread = genrate_thread()
    st.session_state['thread_id'] = new_thread
    

    st.session_state.messages = []
    st.rerun()

st.sidebar.header("My conversations")

# for val in st.session_state['thread_naming']:
    # print(val['thread_id'],val['title'])


for val in reversed(st.session_state['thread_naming']):
    
    if st.sidebar.button(val['title']):
        load_chat(val['thread_id'])
    


#------------------------------other logics -------------------------------------------------------------------------------


CONFG = {'configurable':{"thread_id":st.session_state['thread_id']}}


for message in st.session_state.messages:
    
    with st.chat_message(message['role']):
        st.write(message['message'])



user_input = st.chat_input("Type here ")

if user_input:

    

    st.session_state.messages.append({'role':"user" , "message":user_input})

    with st.chat_message("user"):
        st.write(user_input)



    with st.chat_message('assistant'):
        with st.spinner("Thinking...."):
            AI_message = st.write_stream(
                    (
                        message_chunk.content
                        for message_chunk, metadata in chatbot.stream(
                            {'messages': [HumanMessage(content=user_input)]},
                            config=CONFG,
                            stream_mode="messages"
                        )
                    )
            )

    title = genrate_thread_titles(st.session_state['thread_id'])
    
    save_threads(st.session_state['thread_id'] , title)

    
        #     AI_res = chatbot.invoke({'messages':[HumanMessage(content=user_input)]} , config=CONFG)

        # AI_message = AI_res['messages'][-1].content

            

        

    

    st.session_state.messages.append({"role":"assistant" , "message":AI_message})

    st.rerun()
