from django import forms
from .models import User

class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                widget.attrs['class'] = 'form-control'

class StaffCreateForm(BootstrapMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class StaffEditForm(BootstrapMixin, forms.ModelForm):
    new_password = forms.CharField(
        required=False, widget=forms.PasswordInput,
        help_text='Leave blank to keep the current password.')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'is_active']

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data['new_password']:
            user.set_password(self.cleaned_data['new_password'])
        if commit:
            user.save()
        return user