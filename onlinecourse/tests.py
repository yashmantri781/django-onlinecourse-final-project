from django.test import TestCase
from django.contrib.auth.models import User
from .models import Course, Lesson, Question, Choice, Enrollment, Submission


class QuestionChoiceSubmissionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student1', password='testpassword123')
        self.course = Course.objects.create(name='Django Cloud Course', description='Test course description')
        self.lesson = Lesson.objects.create(title='Django Models', course=self.course, content='Lesson content')
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)

        # Single-correct-choice question
        self.q1 = Question.objects.create(
            lesson=self.lesson,
            question_text='Which language is Django written in?',
            grade=50
        )
        self.q1_c1 = Choice.objects.create(question=self.q1, choice_text='Python', is_correct=True)
        self.q1_c2 = Choice.objects.create(question=self.q1, choice_text='Java', is_correct=False)
        self.q1_c3 = Choice.objects.create(question=self.q1, choice_text='C++', is_correct=False)

        # Multi-correct-choice question
        self.q2 = Question.objects.create(
            lesson=self.lesson,
            question_text='Which of the following are Django components?',
            grade=50
        )
        self.q2_c1 = Choice.objects.create(question=self.q2, choice_text='Models', is_correct=True)
        self.q2_c2 = Choice.objects.create(question=self.q2, choice_text='Views', is_correct=True)
        self.q2_c3 = Choice.objects.create(question=self.q2, choice_text='React Native', is_correct=False)

    def test_single_choice_grading(self):
        # Correct answer
        self.assertTrue(self.q1.is_get_score([self.q1_c1.id]))
        # Wrong answer
        self.assertFalse(self.q1.is_get_score([self.q1_c2.id]))
        # Correct + wrong answer
        self.assertFalse(self.q1.is_get_score([self.q1_c1.id, self.q1_c2.id]))
        # No answer
        self.assertFalse(self.q1.is_get_score([]))

    def test_multiple_choice_grading(self):
        # All correct answers selected
        self.assertTrue(self.q2.is_get_score([self.q2_c1.id, self.q2_c2.id]))
        # Only one of two correct answers selected (partial)
        self.assertFalse(self.q2.is_get_score([self.q2_c1.id]))
        # Both correct + one wrong answer selected
        self.assertFalse(self.q2.is_get_score([self.q2_c1.id, self.q2_c2.id, self.q2_c3.id]))
        # Only wrong answer selected
        self.assertFalse(self.q2.is_get_score([self.q2_c3.id]))

    def test_submission_creation(self):
        sub = Submission.objects.create(enrollment=self.enrollment)
        sub.choices.add(self.q1_c1, self.q2_c1, self.q2_c2)
        self.assertEqual(sub.choices.count(), 3)
        self.assertIn(self.q1_c1, sub.choices.all())
        self.assertEqual(self.q1.course, self.course)

    def test_submit_view_and_exam_result(self):
        self.client.login(username='student1', password='testpassword123')
        # Submit correct answers
        response = self.client.post(f'/onlinecourse/{self.course.id}/submit/', {
            f'choice_{self.q1_c1.id}': self.q1_c1.id,
            f'choice_{self.q2_c1.id}': self.q2_c1.id,
            f'choice_{self.q2_c2.id}': self.q2_c2.id,
        })
        self.assertEqual(response.status_code, 302)
        submission = Submission.objects.filter(enrollment=self.enrollment).first()
        self.assertIsNotNone(submission)

        # Check result view
        res = self.client.get(f'/onlinecourse/course/{self.course.id}/submission/{submission.id}/result/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['grade'], 100)
        self.assertContains(res, "Congratulations!")
        self.assertContains(res, "100/100")

    def test_unauthorized_user_cannot_access_submission(self):
        other_user = User.objects.create_user(username='student2', password='testpassword123')
        sub = Submission.objects.create(enrollment=self.enrollment)

        # Log in as other user
        self.client.login(username='student2', password='testpassword123')
        res = self.client.get(f'/onlinecourse/course/{self.course.id}/submission/{sub.id}/result/')
        # Should be redirected away from other user's exam result
        self.assertEqual(res.status_code, 302)


