from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating-input'}),
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'review_text']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-lg glass-input',
                'placeholder': 'Summarize your experience',
                'maxlength': 200,
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control glass-input',
                'rows': 5,
                'placeholder': 'Tell others about your experience...',
            }),
        }
        labels = {
            'title': 'Review Title',
            'review_text': 'Your Review',
        }
