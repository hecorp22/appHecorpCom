def lambda_handler(event,context):
	name=event.get("name","Hello from Atlantida-HELLO WOLRD")
	message=f"Hola {name}, desde AWS LAMBDA"

	return {
		"statusCode":200,
		"body":message
	}