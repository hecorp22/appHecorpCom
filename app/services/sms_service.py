from twilio.rest import Client
import os
from loguru import logger
from prometheus_client import Counter, Histogram
import time

SMS_SENT = Counter("sms_sent_total", "SMS enviados", ["status", "provider"])
SMS_DUR  = Histogram("sms_send_duration_seconds", "Duración envío SMS", ["provider"])

class SmsService:
    def __init__(self):
        self.sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_ = os.getenv("TWILIO_SMS_FROM")
        self.client = Client(self.sid, self.token)

    def send(self, to: str, body: str) -> str:
        t0 = time.perf_counter()
        try:
            msg = self.client.messages.create(to=to, from_=self.from_, body=body)
            SMS_SENT.labels(status="success", provider="twilio").inc()
            return msg.sid
        except Exception as e:
            logger.exception("sms_error", to=to)
            SMS_SENT.labels(status="fail", provider="twilio").inc()
            raise e
        finally:
            SMS_DUR.labels(provider="twilio").observe(time.perf_counter() - t0)
