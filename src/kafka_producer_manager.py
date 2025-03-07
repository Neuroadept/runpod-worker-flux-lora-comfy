import os
from contextlib import contextmanager
from typing import Generator, Self

import json
from kafka import KafkaProducer


class KafkaManager:
    def __init__(self, producer: KafkaProducer, topic_name: str):
        self.producer = producer
        self.topic_name = topic_name

    @staticmethod
    def check_and_get_kafka_creds() -> tuple[str, str, str, str]:
        fqdn = os.getenv("VIBEAI_KAFKA_FQDN")
        user = os.getenv("VIBEAI_KAFKA_USER")
        password = os.getenv("VIBEAI_KAFKA_PASSWORD")
        kafka_topic_name = os.getenv("VIBEAI_KAFKA_TOPIC_NAME")
        if not all((fqdn, user, password, kafka_topic_name)):
            raise ValueError("Not all kafka credentials specified.")
        return fqdn, user, password, kafka_topic_name

    @classmethod
    @contextmanager
    def get_and_close(cls) -> Generator[Self, any, any]:
        fqdn, user, password, kafka_topic_name = cls.check_and_get_kafka_creds()
        producer = KafkaProducer(
            bootstrap_servers=f"{fqdn}:9091",
            security_protocol="SASL_SSL",
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username=user,
            sasl_plain_password=password,
            ssl_cafile="/usr/local/share/ca-certificates/Yandex/YandexInternalRootCA.crt",
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(3, 5, 0),
        )
        try:
            yield cls(producer=producer, topic_name=kafka_topic_name)
        finally:
            producer.flush()
            producer.close()

    def _push(
            self,
            data: dict
    ) -> None:
        self.producer.send(self.topic_name, data)
        self.producer.flush()

    def push_inference_completed_msg(
            self,
            chat_id: int,
            job_id: str,
            upload_path: str,
    ) -> None:
        data = {
            "chat_id": chat_id,
            "rp_job_id": job_id,
            "upload_path": upload_path,
        }
        self._push(data)

    def push_error_msg(
            self,
            job_id: str,
            error_type: str,
            error_msg: str,
            trace: str,
            job_input: dict,
    ) -> None:
        data = {
            "job_id": job_id,
            "error_type": error_type,
            "error_msg": error_msg,
            "trace": trace,
            "job_input": job_input,
        }
        self._push(data)
