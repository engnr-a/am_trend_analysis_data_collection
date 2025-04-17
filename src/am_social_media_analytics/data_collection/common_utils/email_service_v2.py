from prefect import flow, task, get_run_logger
from prefect_email import EmailServerCredentials, email_send_message
from datetime import datetime
from prefect_email import EmailServerCredentials, email_send_message

from email.message import EmailMessage

from prefect.context import FlowRunContext, TaskRunContext
@task
def send_flow_info_by_email(email_type, to_email_addresses, flow_name, parameters, additional_data):
    try:
        
        logger = get_run_logger()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        node_id = additional_data.get("node_id", "UNKNOWN").upper()
        
        # Determine the actual message content based on email_type
        if email_type == "start":
            action = "has started"
        elif email_type == "ended":
            action = "has ended"
        else:
            action
            
        node_emojis = {
            "node1": "1️⃣",
            "node2": "2️⃣",
            "node3": "3️⃣",
            "node4": "4️⃣",
        }
        
        emoji = node_emojis.get(node_id.lower(), "❓")  
        #title_template = f"{node_id} Work Flow: {{flow_name}} {{action}}"
        
        title_template = f"{emoji} {node_id.upper()} Work Flow: {{flow_name}} {{action}}"

        message = (
            f"<p>Hello,</p>"
            f"<p>This email is sent from the {emoji} {node_id.upper()} work flow named <b>'{flow_name}'</b>. "
            f"<p><b>Execution Start Time</b>: {current_time}</p>"
            f"<p><b>Parameters</b> passed to the flow:</p>"
            f"<ul>{''.join([f'<li><b>{key}</b>: {value}</li>' for key, value in parameters])}</ul>"
            f"<p><b>Additional Data</b>: consumed by the workflow</p>"
            f"<ul>{''.join([f'<li><b>{key}</b>: {value}</li>' for key, value in additional_data.items()])}</ul>"
            f"<p>Best regards,</p>"
            f"<p>Shola Suleiman</p>"
        )
        
            
        # Construct the subject and message
        subject_of = title_template.format(flow_name=flow_name, action=action)

        # Create email object with explicit formatting
        email_msg = EmailMessage()
        email_msg["From"] = "abubakar.suleiman@tuhh.de"
        email_msg["To"] = ", ".join(to_email_addresses)
        email_msg["Subject"] = subject_of
        email_msg.set_content(message)  
    
        email_server_credentials = EmailServerCredentials.load("emailcredentials")
        for email_address in to_email_addresses:
            
            future = email_send_message.with_options(name=f"{email_type}").submit(
                email_server_credentials=email_server_credentials,
                subject=email_msg["Subject"],
                msg=email_msg.get_content(),  # Properly formatted body
                email_to=email_address,
                email_from=email_msg["From"]
            )
            future.result()
    except Exception as e:
        logger.error(f"❌ Error sending email: {e}", exc_info=True)
        raise


@flow
def email_service_flow(email_type, to_email_addresses, additional_data):
    try:
        context = FlowRunContext.get()
        
        # Access flow name and parameters from the context
        flow_name = context.flow.name
        parameters = context.parameters.items()
        # Call the email task
        send_flow_info_by_email(
            email_type,
            to_email_addresses,
            flow_name,
            parameters,
            additional_data,
        )
    except Exception as e:
        logger = get_run_logger()
        logger.error(f"❌ Error sending email: {e}", exc_info=True)
        raise


@task
def send_search_query_update_email(email_list, tweet_key, search_query, node_id):
    try:
        
        #node_id = additional_data.get("node_id", "UNKNOWN").upper()

        node_emojis = {
            "node1": "1️⃣",
            "node2": "2️⃣",
            "node3": "3️⃣",
            "node4": "4️⃣",
        }
        emoji = node_emojis.get(node_id.lower(), "❓")  
        
        
        logger = get_run_logger()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Construct the subject and message content
        subject = f"{emoji} {node_id} -⚠️ ⚠️ Search Query Update Notification"
        message = (
            f"<p>Hello,</p>"
            f"<p>This email is sent from the {emoji} <b>{node_id}</b> node.</p>"
            f"<p>As of {current_time}, a condition that warrants the change of the search query has been encountered.</p>"
            f"<p>The following Unique Tweet Key: <b>{tweet_key}</b> has been repeatedly encountered multiple times.</p>"
            f"<p>Hence, the <b>until</b> date part of the search query will be moved downward by 1 day.</p>"
            f"<p>Here is the updated search query:</p>"
            f"<p><b>{search_query}</b></p>"
            f"<p>Best regards,</p>"
            f"<p>Shola Suleiman</p>"
        )

        # Create email object
        email_msg = EmailMessage()
        email_msg["From"] = "abubakar.suleiman@tuhh.de"
        email_msg["Subject"] = subject
        email_msg.set_content(message, subtype='html')

        # Load email server credentials
        email_server_credentials = EmailServerCredentials.load("emailcredentials")

        for email_address in email_list:
            email_msg["To"] = email_address

            # Send the email
            future = email_send_message.with_options(name=f"send_notification_to_{email_address}").submit(
                email_server_credentials=email_server_credentials,
                subject=subject,
                msg=email_msg.get_content(),
                email_to=email_address,
                email_from=email_msg["From"]
            )

            # Await result to handle any errors
            future.result()

        logger.info("✅ == Search Query Update Email == sent successfully to all recipients.")

    except Exception as e:
        logger.error(f"❌ Error sending email: {e}", exc_info=True)
        raise


@task
def send_search_window_summary_email(email_list, node_id, since_date, until_date, query):
    try:
        logger = get_run_logger()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        node_emojis = {
            "node1": "1️⃣",
            "node2": "2️⃣",
            "node3": "3️⃣",
            "node4": "4️⃣",
        }
        emoji = node_emojis.get(node_id.lower(), "❓")

        subject = f"{emoji} {node_id} - 🗓️ Query Lag Handling Info"

        message = (
            f"<p>Hello,</p>"
            f"<p>This is an automated summary from node <b>{emoji} {node_id}</b>.</p>"
            f"<p><b>Execution Time</b>: {current_time}</p>"
            f"<p><b>Search window:</b></p>"
            f"<p>THE LAST RUN FALLS WITHIN THE LAST 4 HOURS OF THE DAY..HENCE, LAG IS IGNOREED</p>"
            f"<ul>"
            f"<li><b>Since date</b>: {since_date}</li>"
            f"<li><b>Until date</b>: {until_date}</li>"
            f"</ul>"
            f"<p><b>Search Query Used:</b></p>"
            f"<p><code>{query}</code></p>"
            f"<p>Best regards,</p>"
            f"<p>Shola Suleiman</p>"
        )

        email_msg = EmailMessage()
        email_msg["From"] = "abubakar.suleiman@tuhh.de"
        email_msg["Subject"] = subject
        email_msg.set_content(message, subtype='html')

        email_server_credentials = EmailServerCredentials.load("emailcredentials")

        for email_address in email_list:
            email_msg["To"] = email_address

            future = email_send_message.with_options(name=f"search_summary_{email_address}").submit(
                email_server_credentials=email_server_credentials,
                subject=subject,
                msg=email_msg.get_content(),
                email_to=email_address,
                email_from=email_msg["From"]
            )
            future.result()

        logger.info("✅ Search window summary email sent to all recipients.")

    except Exception as e:
        logger.error(f"❌ Error sending summary email: {e}", exc_info=True)
        raise
    
@task
def send_generic_email(email_list: list, subject: str, message: str):
    try:
        logger = get_run_logger()
        email_msg = EmailMessage()
        email_msg["From"] = "abubakar.suleiman@tuhh.de"
        email_msg["Subject"] = subject
        email_msg.set_content(message, subtype='html')

        email_server_credentials = EmailServerCredentials.load("emailcredentials")

        for email_address in email_list:
            email_msg["To"] = email_address

            future = email_send_message.with_options(name=f"generic_email_to_{email_address}").submit(
                email_server_credentials=email_server_credentials,
                subject=subject,
                msg=email_msg.get_content(),
                email_to=email_address,
                email_from=email_msg["From"]
            )
            future.result()

        logger.info("📩 Generic email sent to all recipients.")

    except Exception as e:
        logger.error(f"❌ Error sending generic email: {e}", exc_info=True)
        raise
@flow
def test():
    email_list = ["sholasuleiman1@gmail.com"]

    # Key of the repeated tweet
    tweet_key = "duplicate_tweet_key_123"

    # Updated search query
    search_query = "updated_search_query=until:2025-01-02"

    
    # Call the task with .delay() for deferred execution
    future = send_search_query_update_email(email_list, tweet_key, search_query)
    #result = future.result()  # Wait for the task to complete if needed

if __name__ == "__main__":
    
    
    
    ####################################################################################
    test()
