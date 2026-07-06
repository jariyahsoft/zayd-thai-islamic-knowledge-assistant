import sys

from zayd_common.database import SQLAlchemyUnitOfWork, get_sessionmaker, seed_demo_data
from zayd_common.settings import ServiceSettings


def main() -> None:
    """Entry point for seeding the database with demo fixtures."""
    settings = ServiceSettings.from_runtime_env(app_name="seeding")
    session_factory = get_sessionmaker(settings.database_url)
    uow = SQLAlchemyUnitOfWork(session_factory)

    db_endpoint = settings.database_url.split("@")[-1]
    print(f"Connecting and seeding database at: {db_endpoint}")

    try:
        passwords = seed_demo_data(uow)
        print("Demo database fixtures seeded successfully!")

        if passwords:
            print("\nWARNING: Generated demo credentials:")
            for email, password in passwords.items():
                print(f"  Email:    {email}")
                print(f"  Password: {password}")
            print("\nThese demo credentials are temporary. Rotate them before any real use.")
    except Exception as exc:
        print(f"Fatal error seeding database: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
