from prefect_email import EmailServerCredentials


credentials = EmailServerCredentials(
     username="cgg7816",  
     password=f"", #NOTHING TO SEE HERE ! lol
     smtp_server="mail.tu-harburg.de", # Essentially for tuhh
     smtp_port=465,
     use_tls=True
)
credentials.save("emailcredentials", overwrite=True)
