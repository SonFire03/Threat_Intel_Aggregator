from app.models.enums import IOCType
from app.normalizers.domain_normalizer import normalize_domain
from app.normalizers.hash_normalizer import normalize_hash
from app.normalizers.ip_normalizer import normalize_ip
from app.normalizers.url_normalizer import normalize_url


def test_private_ipv4_is_flagged() -> None:
    result = normalize_ip("192.168.1.10")
    assert result.ioc_type == IOCType.IPV4
    assert result.value == "192.168.1.10"
    assert result.is_private_ip is True


def test_ipv6_is_canonicalized() -> None:
    first = normalize_ip("2001:0db8:0000:0000:0000:ff00:0042:8329")
    second = normalize_ip("2001:db8::ff00:42:8329")

    assert first.ioc_type == IOCType.IPV6
    assert first.value == second.value


def test_domain_lowercases_and_strips_www_and_trailing_dot() -> None:
    result = normalize_domain("WWW.Example.COM.")
    assert result.ioc_type == IOCType.DOMAIN
    assert result.value == "example.com"


def test_defanged_url_is_refanged_and_fragment_removed() -> None:
    result = normalize_url("hxxps://evil[.]com/path#fragment")
    assert result.ioc_type == IOCType.URL
    assert result.value == "https://evil.com/path"


def test_md5_is_uppercased_and_empty_hash_flagged() -> None:
    empty_md5 = normalize_hash("d41d8cd98f00b204e9800998ecf8427e")
    malware_md5 = normalize_hash("44d88612fea8a8f36de82e1278abb02f")

    assert empty_md5.value == "D41D8CD98F00B204E9800998ECF8427E"
    assert empty_md5.ioc_type == IOCType.MD5
    assert empty_md5.is_empty_hash is True

    assert malware_md5.value == "44D88612FEA8A8F36DE82E1278ABB02F"
    assert malware_md5.is_empty_hash is False
