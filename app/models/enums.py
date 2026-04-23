from enum import StrEnum


class IOCType(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    CVE = "cve"


class SourceType(StrEnum):
    FILE = "file"
    API = "api"
    MANUAL = "manual"
    FEED = "feed"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    TXT = "txt"
