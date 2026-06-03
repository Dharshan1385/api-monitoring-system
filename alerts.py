from twilio.rest import Client

ACCOUNT_SID = "AC79eb3ed5f2d1f18eb82b08f5b7a929fb"
AUTH_TOKEN = "31a2e3bab51def40a4b1e728ed3ae60d"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

FROM_NUMBER = "+14244046271"

TO_NUMBER = "+918309753179"


def send_sms(message):
    try:
        msg = client.messages.create(
            body=message,
            from_=FROM_NUMBER,
            to=TO_NUMBER
        )

        print("🚨 SMS SENT SUCCESSFULLY:", msg.sid)

    except Exception as e:
        print("❌ SMS FAILED:", str(e))