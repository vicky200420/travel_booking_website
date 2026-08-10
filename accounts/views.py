from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from .forms import LoginForm, ProfileEditForm, RegistrationForm
from .models import CustomUser


class RegisterView(SuccessMessageMixin, CreateView):
    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('login')
    success_message = 'Registration successful! You can now log in.'


class LoginView(SuccessMessageMixin, FormView):
    form_class = LoginForm
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('dashboard')
    success_message = 'Welcome back!'

    def form_valid(self, form):
        user = form.cleaned_data['user']
        login(self.request, user)
        return super().form_valid(form)


class LogoutView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return []

    def render_to_response(self, context, **response_kwargs):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.success(self.request, 'You have been logged out successfully.')
        return redirect('home')


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'


class VerifyEmailView(TemplateView):
    template_name = 'accounts/verify_email.html'

    def get_context_data(self, token, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model

        from notifications.services import NotificationService
        from notifications.utils import load_verification_token

        email = load_verification_token(token)
        user = None
        if email:
            user = get_user_model().objects.filter(email__iexact=email).first()

        if user and user.is_email_verified:
            context.update(verified=True, already=True, user=user)
            return context

        if user:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified', 'updated_at'])
            from notifications.models import Notification
            NotificationService.create(
                user, 'Email verified',
                'Your email address has been confirmed. Thank you!',
                Notification.Type.SUCCESS,
                '/dashboard/', 'bi-envelope-check-fill',
                {'event': 'email_verified'},
            )
            context.update(verified=True, already=False, user=user)
            return context

        context.update(verified=False)
        return context


class EditProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = 'accounts/edit_profile.html'
    success_message = 'Profile updated successfully.'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('profile')
