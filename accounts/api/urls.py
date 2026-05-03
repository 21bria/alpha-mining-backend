from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.api.views import LoginView, MeView, SetActiveIUPView

router = DefaultRouter()

from accounts.api.admin.views import AdminUserViewSet
from accounts.api.group.views import AdminGroupViewSet
from accounts.api.group.lookup import GroupLookupViewSet
from accounts.api.permissions.views import PermissionTreeView
from accounts.api.group.permissions import GroupPermissionsView

from accounts.api.security.account_update_view import AccountUpdateView
from accounts.api.security.change_password_view import ChangePasswordView
from accounts.api.profile.views import ProfileView

router.register(r"admin/users", AdminUserViewSet, basename="admin-users")
router.register(r"admin/groups", AdminGroupViewSet, basename="admin-groups")
router.register(r"groups/lookup", GroupLookupViewSet, basename="group-lookup")

urlpatterns = [


    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("active-iup/", SetActiveIUPView.as_view(), name="auth-active-iup"),

    # permission tree
    path("permissions/tree/", PermissionTreeView.as_view(), name="permission-tree"),
    path("admin/groups/<int:pk>/permissions/",GroupPermissionsView.as_view(),),

    # Account & Password
    path("account/update/", AccountUpdateView.as_view(), name="account-update"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path('profile/', ProfileView.as_view(), name='auth-profile'),

    # ADMIN (router)
    path("", include(router.urls)),
]