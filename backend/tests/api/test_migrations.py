from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.models import Base


def test_migrations_match_models(database):
    """Every model change must come with a migration."""
    with database.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []
