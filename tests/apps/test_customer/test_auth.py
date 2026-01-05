"""
Example test file for Customer App endpoints
Run with: pytest tests/apps/test_customer/test_auth.py
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCustomerAuth:
    """Test customer authentication endpoints"""

    def test_register_customer_success(self):
        """Test successful customer registration"""
        response = client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "testcustomer@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Customer"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "customer"
        assert data["token_type"] == "bearer"

    def test_register_customer_duplicate_email(self):
        """Test registration with duplicate email fails"""
        # First registration
        client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Customer"
            }
        )

        # Second registration with same email
        response = client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Customer"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_login_customer_success(self):
        """Test successful customer login"""
        # Register first
        register_data = {
            "email": "logincustomer@example.com",
            "password": "testpass123",
            "first_name": "Login",
            "last_name": "Test"
        }
        client.post("/api/v1/customer/auth/register", json=register_data)

        # Login
        response = client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "logincustomer@example.com",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "customer"

    def test_login_customer_wrong_password(self):
        """Test login with wrong password fails"""
        # Register first
        client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "correctpass",
                "first_name": "Test",
                "last_name": "User"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "wrongpass"
            }
        )
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self):
        """Test login with non-existent user fails"""
        response = client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepass"
            }
        )
        assert response.status_code == 401


class TestCustomerProfile:
    """Test customer profile endpoints"""

    @pytest.fixture
    def customer_token(self):
        """Create a customer and return auth token"""
        response = client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "profilecustomer@example.com",
                "password": "testpass123",
                "first_name": "Profile",
                "last_name": "Customer"
            }
        )
        return response.json()["access_token"]

    def test_get_profile_success(self, customer_token):
        """Test getting customer profile"""
        response = client.get(
            "/api/v1/customer/profile",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profilecustomer@example.com"
        assert data["role"] == "customer"

    def test_get_profile_no_auth(self):
        """Test getting profile without authentication fails"""
        response = client.get("/api/v1/customer/profile")
        assert response.status_code == 401

    def test_update_profile_success(self, customer_token):
        """Test updating customer profile"""
        response = client.patch(
            "/api/v1/customer/profile",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "first_name": "Updated",
                "last_name": "Name"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"


class TestRoleBasedAccess:
    """Test that role-based access control works correctly"""

    @pytest.fixture
    def rider_token(self):
        """Create a rider and return auth token"""
        response = client.post(
            "/api/v1/rider/auth/register",
            json={
                "email": "testrider@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Rider"
            }
        )
        return response.json()["access_token"]

    def test_rider_cannot_access_customer_endpoints(self, rider_token):
        """Test that rider token cannot access customer endpoints"""
        response = client.get(
            "/api/v1/customer/profile",
            headers={"Authorization": f"Bearer {rider_token}"}
        )
        assert response.status_code == 403
        assert "customer access required" in response.json()["detail"].lower()

    @pytest.fixture
    def restaurant_token(self):
        """Create a restaurant owner and return auth token"""
        response = client.post(
            "/api/v1/restaurant/auth/register",
            json={
                "email": "testowner@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "Owner"
            }
        )
        return response.json()["access_token"]

    def test_restaurant_cannot_access_rider_endpoints(self, restaurant_token):
        """Test that restaurant token cannot access rider endpoints"""
        response = client.get(
            "/api/v1/rider/profile",
            headers={"Authorization": f"Bearer {restaurant_token}"}
        )
        assert response.status_code == 403
        assert "driver access required" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

