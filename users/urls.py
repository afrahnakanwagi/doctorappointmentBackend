from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/activate/', views.UserActivationView.as_view(), name='user-activate'),
    path('users/<int:pk>/deactivate/', views.UserDeactivationView.as_view(), name='user-deactivate'),
    path('profile/', views.UserProfileEditView.as_view(), name='user-profile-edit'),
] 