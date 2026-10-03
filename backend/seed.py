from sqlmodel import Session, select

from .database import engine, init_db
from .models import KBArticle


def seed() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(KBArticle)).first():
            return
        session.add_all([
            KBArticle(title="Checkout connection pool exhaustion after deploy", category="Availability", content_md="""## Symptoms\nCheckout 5xx errors begin shortly after a release; the connection pool reaches its configured maximum.\n\n## Response\n1. Confirm the deploy time aligns with the error spike.\n2. Check pool saturation and connection wait time.\n3. If impact is ongoing, roll back to the last known good version after approval.\n4. Verify error rate and pool utilization recover."""),
            KBArticle(title="Correlating upstream retries", category="Observability", content_md="""Follow shared trace IDs across service logs. A downstream retry storm can amplify a single upstream failure; preserve the initiating error as the likely causal event."""),
        ])
        session.commit()


if __name__ == "__main__":
    seed()
