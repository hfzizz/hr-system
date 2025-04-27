from django import forms
from teaching_portfolio.models import TeachingPortfolio, TeachingModule

class TeachingPortfolioForm(forms.ModelForm):
    class Meta:
        model = TeachingPortfolio
        exclude = ['user']
        widgets = {
            field: forms.Textarea(attrs={
                'rows': 3,
                'class': 'block w-full rounded-md border border-gray-300 py-2 px-3 text-gray-900 shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            }) for field in [
                'teaching_philosophy_full', 'teaching_philosophy_summary',
                'learning_outcome_full', 'learning_outcome_summary',
                'instructional_methodology_full', 'instructional_methodology_summary',
                'other_means_to_enhance_learning_full', 'other_means_to_enhance_learning_summary',
                'other_teaching_full',
                'academic_leadership_full', 'academic_leadership_summary',
                'contribution_teaching_materials_full', 'contribution_teaching_materials_summary',
                'future_teaching_goals_full', 'future_teaching_goals_summary',
                'future_steps_improve_teaching_full', 'future_steps_improve_teaching_summary'
            ]
        }


class TeachingModuleForm(forms.ModelForm):
    class Meta:
        model = TeachingModule
        fields = [
            'module_title',
            'level',
            'language_medium',
            'student_count',
            'joint_teaching_percentage',
            'hours_weekly'
        ]
        widgets = {
            'module_title': forms.TextInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
            'level': forms.TextInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
            'language_medium': forms.TextInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
            'student_count': forms.NumberInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
            'joint_teaching_percentage': forms.NumberInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
            'hours_weekly': forms.NumberInput(attrs={'class': 'w-full p-2 rounded border border-gray-300'}),
        }
