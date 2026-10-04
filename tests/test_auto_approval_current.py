from app.state import State
from app.gateway import Gateway
from app.merchants import addr

def test_trusted_verified_booking_under_1500_is_executed_immediately():
    gw = Gateway("u_test", "test", b"test-master-key")
    dev = gw.add_device("Test laptop", trusted=True)
    sess = gw.ensure_session("ses_test", dev["id"])
    it = gw.submit_intent(sess, origin="user", type="hotel", merchant_domain="grandstay.mock",
        pay_to=addr("grandstay"), amount=800, purpose="Pink City Residency (1 night, Jaipur)",
        payload={"title":"Pink City Residency","city":"Jaipur","units":1,"unit_price":800,"unit_label":"night"})
    assert it["decision"]["verdict"] == "ALLOW"
    assert it["status"] == "executed"
    assert it["booking_id"]
    assert it["tx_hash"]
