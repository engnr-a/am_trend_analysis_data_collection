from prefect.blocks.system import Secret

#linkedinusername = Variable.get('linkedinusername')
linkedinpassword = Secret.load("twitterpassword").get()
print(linkedinpassword)