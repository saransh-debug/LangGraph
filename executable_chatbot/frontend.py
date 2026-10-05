import streamlit as st 
from langchain_core.messages import  HumanMessage , AIMessage ,ToolMessage
from langchain_core.runnables import RunnableConfig
import backend
import uuid
from background_thread import runtime
import asyncio
import queue

def run_async(coroutine):#used to execute and async function and return its actual result
    return runtime.run(coroutine)

# ------------------------------------------------------ utility functions---------------------------------------------
def genrate_thread():
    thread = uuid.uuid4()
    
    return str(thread)



# --------------------------------------------------
# LOAD CHAT
# --------------------------------------------------
async def load_chat(thread_id):
    temp_list = []
    output = await backend.chatbot.aget_state({'configurable':{"thread_id":thread_id}})
    messages = output.values.get("messages",[])

    for msg in messages:
        if isinstance(msg, HumanMessage):
            temp_list.append({"role": "user", "message": msg.content})
        elif isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None):
            if isinstance(msg.content, str):
                temp_list.append({"role": "assistant", "message": msg.content})

    # st.session_state['messages'] = temp_list
    # st.session_state['thread_id']=thread_id
    return temp_list
    

# def save_thread_titles(thread_id,title):
#     if thread_id not in [item['thread_id'] for item in st.session_state['thread_naming']]:
#             st.session_state['thread_naming'].append({"thread_id":thread_id , "title":title})


# --------------------------------------------------
# GENERATE TITLE
# --------------------------------------------------


async def genrate_thread_titles(thread_id):
   
    temp_list = []
    output =await  backend.chatbot.aget_state({'configurable':{"thread_id":thread_id}})
    
    messages = output.values.get('messages',[])
    
    if messages is None:
        return "New Chat"
    
    for msg in messages:
        if isinstance(msg , HumanMessage):
                role = "user"
        else:
                role="assistant"
        temp_list.append({"role":role , "message":msg.content})
    
    res =await backend.model.ainvoke(f"""
        Give me a short title for this conversation.

        Requirements:
        - Minimum 2 words
        - Maximum 5 words
        - No quotation marks

        Conversation:
        {temp_list[:10]}
        """)
    
    
    return res.content

print("above main ")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("main started")

    if not getattr(backend, 'chatbot', None):
        run_async(backend.start_graph()) #a function in backend.py to start the database and the backend processes

    # -------------------------------state tools management-----------------------------------------------------------------


    if 'thread_naming' not in st.session_state:
        st.session_state['thread_naming']=run_async(backend.get_threads_data())  # backend function 




    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = genrate_thread()


    if "messages" not in st.session_state:
        st.session_state['messages'] = []



    # ----------------------------------------------------sidebar panel------------------------------------------------
    st.sidebar.title("Your chats")

    if st.sidebar.button("New chat"):
        
        st.session_state['thread_id'] = genrate_thread()
        

        st.session_state.messages = []
        st.rerun()

    st.sidebar.header("My conversations")

    # for val in st.session_state['thread_naming']:
        # print(val['thread_id'],val['title'])


    for val in reversed(st.session_state['thread_naming']):
        
        if st.sidebar.button(val['title'] , key=f"thread_{val['thread_id']}"):
            
            loaded_messages = run_async(load_chat(val['thread_id']))

            st.session_state['messages'] = loaded_messages
            st.session_state['thread_id'] = val['thread_id']
        
            st.rerun()

    #------------------------------CONFIG-------------------------------------------------------------------------------


    CONFG = {'configurable':{"thread_id":st.session_state['thread_id']},
            "metadata":{
                "thread_id":st.session_state['thread_id']
            },
            "run_name":"Chatbot_Traces"}

    
# --------------------------------------------------
    # DISPLAY EXISTING MESSAGES
    # --------------------------------------------------


    for message in st.session_state.messages:
        
        with st.chat_message(message['role']):
            st.write(message['message'])

#-----------------USER INPUT -----------------------------

    user_input = st.chat_input("Type here ")

    if not user_input:return 


    
    if user_input:

        

        st.session_state.messages.append(
            {'role':"user" ,
              "message":user_input}
              )

        with st.chat_message("user"):
            st.write(user_input)

#-----------------------------------assitant-----------------------------------------------------------

        with st.chat_message('assistant'):
            status_box = None
            assistant_response = []

            def ai_only_stream():
                nonlocal status_box
                event_queue = queue.Queue()
                
            # with st.spinner("Thinking...."):
                
                async def ai_only_res():
                    try:
                        async for message_chunk, metadata in backend.chatbot.astream(
                            {'messages': [HumanMessage(content=user_input)]},
                            config=CONFG,
                            stream_mode="messages"
                        ):
                            event_queue.put((message_chunk, metadata))
                    except Exception as error:
                        event_queue.put(("error", error))
                    finally:
                        event_queue.put(None)

                future = runtime.submit(ai_only_res())

                while True:
                    try:
                        item = event_queue.get(timeout=0.5)
                    except queue.Empty:
                        if future.done():
                            future.result()
                        continue

                    if item is None:
                        future.result()
                        break

                    if item[0] == "error":
                        raise item[1]

                    message_chunk, metadata = item

                    if isinstance(message_chunk, ToolMessage):
                        tool_name = getattr(message_chunk, "name", "tool")

                        if status_box is None:
                            status_box = st.status(
                                f"🔧 Using `{tool_name}` …", expanded=True
                            )
                        else:
                            status_box.update(
                                label=f"🔧 Using `{tool_name}` …",
                                state="running",
                                expanded=True,
                            )

                    elif isinstance(message_chunk, AIMessage):
                        text = message_chunk.content or ""
                        if isinstance(text, str):
                            assistant_response.append(text)
                            yield text

            st.write_stream(ai_only_stream())

            if status_box is not None:
                status_box.update(label="✅Done",
                                  state="complete",
                                  expanded=False)

        AI_message = "".join(assistant_response)

        #-----------saving threads------------------------
        thread_id = st.session_state['thread_id']
        existing_thread_ids = {
            item['thread_id'] for item in st.session_state['thread_naming']
        }

        if thread_id not in existing_thread_ids:
            title = run_async(genrate_thread_titles(thread_id))

            run_async(backend.save_threads(thread_id, title))

            st.session_state["thread_naming"].append(
            {
                "thread_id": thread_id,
                "title": title
            }
        )

        st.session_state.messages.append({"role": "assistant", "message": AI_message})

        st.rerun()

        
        
            #     AI_res = chatbot.invoke({'messages':[HumanMessage(content=user_input)]} , config=CONFG)

            # AI_message = AI_res['messages'][-1].content



if __name__ == "__main__":
    main()    
