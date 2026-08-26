"""
ทดสอบ fas/opennds_proto.py — โปรโตคอลคุยกับ openNDS (fas_secure_enabled = 2)

ยืนยันด้วยตัวเองว่า encrypt<->decrypt สมมาตรกัน (เราคุมทั้งสองฝั่งของการทดสอบนี้เอง
เพราะไม่มี openNDS binary จริงในสภาพแวดล้อมนี้ — ดูคำเตือนใน docstring ของโมดูล)
"""
import pytest

from fas.opennds_proto import (ClientContext, FasProtocolError,
                               auth_token, build_auth_action_url,
                               build_kv_string, decrypt_fas_payload,
                               encrypt_fas_payload, parse_kv_string)

FASKEY = "a1b2c3d4e5f60718293a4b5c6d7e8f90"  # 32 ตัวอักษร เหมือนที่ install.sh สุ่มให้
PARAMS = dict(clientip="10.10.0.105", clientmac="AA:BB:CC:DD:EE:FF",
             gatewayname="Cafe-Guest", client_hid="9f8e7d6c5b4a3f2e1d0c",
             gatewayaddress="10.10.0.1", authdir="opennds_auth",
             originurl="http://example.com/", clientif="eth1")


def test_kv_string_roundtrip():
    s = build_kv_string(PARAMS)
    assert parse_kv_string(s)["clientmac"] == "AA:BB:CC:DD:EE:FF"


def test_parse_kv_string_tolerates_messy_spacing():
    d = parse_kv_string("a=1,  b=2 ,c=3,, d=")
    assert d == {"a": "1", "b": "2", "c": "3", "d": ""}


def test_encrypt_decrypt_roundtrip():
    fas_b64, iv = encrypt_fas_payload(PARAMS, FASKEY)
    ctx = decrypt_fas_payload(fas_b64, iv, FASKEY)
    assert ctx.clientmac == "AA:BB:CC:DD:EE:FF"
    assert ctx.hid == "9f8e7d6c5b4a3f2e1d0c", "client_hid ต้อง map เป็น ctx.hid"
    assert ctx.gatewayaddress == "10.10.0.1"
    assert ctx.is_complete()


def test_iv_is_random_each_time():
    _, iv1 = encrypt_fas_payload(PARAMS, FASKEY)
    _, iv2 = encrypt_fas_payload(PARAMS, FASKEY)
    assert iv1 != iv2


def test_ciphertext_does_not_contain_plaintext():
    fas_b64, _ = encrypt_fas_payload(PARAMS, FASKEY)
    assert "AA:BB:CC:DD:EE:FF" not in fas_b64


def test_wrong_faskey_raises():
    fas_b64, iv = encrypt_fas_payload(PARAMS, FASKEY)
    with pytest.raises(FasProtocolError):
        decrypt_fas_payload(fas_b64, iv, "b" * 32)


def test_empty_payload_raises():
    with pytest.raises(FasProtocolError):
        decrypt_fas_payload("", "", FASKEY)


def test_malformed_base64_raises():
    _, iv = encrypt_fas_payload(PARAMS, FASKEY)
    with pytest.raises(FasProtocolError):
        decrypt_fas_payload("not-valid-base64!!!", iv, FASKEY)


def test_short_faskey_rejected_at_encrypt():
    with pytest.raises(FasProtocolError):
        encrypt_fas_payload(PARAMS, "too-short")


def test_wrong_iv_length_rejected():
    fas_b64, _ = encrypt_fas_payload(PARAMS, FASKEY)
    with pytest.raises(FasProtocolError):
        decrypt_fas_payload(fas_b64, "short", FASKEY)


def test_cbc_has_no_integrity_check_known_limitation():
    """
    บันทึกไว้เป็นเอกสาร (ไม่ใช่บั๊กของเรา): AES-256-CBC ตามที่ openNDS level 2 กำหนด
    ไม่มี MAC/authentication tag ผูกกับ ciphertext — การปลอม iv ทำให้ "บล็อกแรก" ของ
    plaintext เพี้ยน แต่บล็อกถัดไปยังถอดได้ตามปกติและ padding ท้ายสุดยังผ่าน จึง "ไม่ error"
    ทั้งที่ข้อมูลถูกดัดแปลง — เป็นข้อจำกัดของโปรโตคอล openNDS เอง ต้องเขียนอธิบายไว้ในเล่ม
    (บทวิเคราะห์ความปลอดภัย) ไม่ใช่ความผิดพลาดของโค้ดนี้
    """
    fas_b64, iv = encrypt_fas_payload(PARAMS, FASKEY)
    tampered_iv = ("0" * 16)
    ctx = decrypt_fas_payload(fas_b64, tampered_iv, FASKEY)  # ไม่ throw
    assert ctx.clientip != PARAMS["clientip"], "บล็อกแรก (clientip) ต้องเพี้ยนเมื่อ iv ผิด"
    assert ctx.gatewayaddress == PARAMS["gatewayaddress"], "บล็อกหลังยังถอดได้ปกติ (คุณสมบัติของ CBC)"


def test_auth_token_deterministic():
    assert auth_token("hid123", FASKEY) == auth_token("hid123", FASKEY)
    assert auth_token("hid123", FASKEY) != auth_token("hid456", FASKEY)
    assert len(auth_token("hid123", FASKEY)) == 64


def test_build_auth_action_url():
    ctx = ClientContext.from_dict(PARAMS)
    url = build_auth_action_url(ctx, FASKEY, redir="http://example.com/page")
    assert url.startswith("http://10.10.0.1/opennds_auth/?tok=")
    assert auth_token(ctx.hid, FASKEY) in url
    assert "redir=" in url


def test_build_auth_action_url_requires_complete_context():
    incomplete = ClientContext(clientmac="", hid="x", gatewayaddress="1.2.3.4", authdir="a")
    with pytest.raises(FasProtocolError):
        build_auth_action_url(incomplete, FASKEY)


def test_client_hid_alias_mapping():
    ctx = ClientContext.from_dict({"client_hid": "xyz", "clientmac": "AA:BB:CC:DD:EE:FF"})
    assert ctx.hid == "xyz"
