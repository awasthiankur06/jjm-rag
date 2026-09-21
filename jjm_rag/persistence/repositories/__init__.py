"""Repository implementations for canonical JJM persistence."""

from .content import CanonicalContentRepository
from .documents import DocumentRepository
from .dimensions import GeographyRepository, IngestionAuditRepository, ReportingRepository
from .observations import ObservationRepository
from .provenance import ProvenanceRepository
from .records import StructuredRecordRepository
from .versions import VersionRepository

__all__ = [
    "CanonicalContentRepository",
    "DocumentRepository",
    "GeographyRepository",
    "ReportingRepository",
    "IngestionAuditRepository",
    "ObservationRepository",
    "ProvenanceRepository",
    "StructuredRecordRepository",
    "VersionRepository",
]
