"""Auth, multi-company, and tenant isolation."""
import uuid


def test_register_login_me(client):
    email = f"a_{uuid.uuid4().hex[:8]}@x.com"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "password1234",
        "company_name": "Apparel Co", "business_type": "smllc", "state": "NJ"})
    assert r.status_code == 201
    assert client.get("/api/auth/me").json()["email"] == email
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login",
                       json={"email": email, "password": "password1234"}).status_code == 200


def test_wrong_password_rejected(client):
    email = f"b_{uuid.uuid4().hex[:8]}@x.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "password1234", "company_name": "X"})
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login",
                       json={"email": email, "password": "wrong"}).status_code == 401


def test_two_companies_per_user(client):
    email = f"c_{uuid.uuid4().hex[:8]}@x.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "password1234",
        "company_name": "His C-Corp", "business_type": "c_corp"})
    client.post("/api/companies", json={"name": "Her LLC", "business_type": "smllc"})
    companies = client.get("/api/companies").json()
    names = {c["name"] for c in companies}
    assert {"His C-Corp", "Her LLC"} <= names


def test_company_isolation(client):
    # user1 makes a company
    client.post("/api/auth/register", json={
        "email": f"d_{uuid.uuid4().hex[:8]}@x.com", "password": "password1234",
        "company_name": "Private Co"})
    cid = client.get("/api/companies").json()[0]["id"]
    client.post("/api/auth/logout")
    # user2 must not access it
    client.post("/api/auth/register", json={
        "email": f"e_{uuid.uuid4().hex[:8]}@x.com", "password": "password1234",
        "company_name": "Other Co"})
    assert client.get(f"/api/companies/{cid}/accounts").status_code == 403
