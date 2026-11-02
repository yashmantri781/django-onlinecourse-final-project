from django.shortcuts import render
from django.http import HttpResponseRedirect
# Import models
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            try:
                choice_id = int(value)
                submitted_answers.append(choice_id)
            except ValueError:
                pass
    return submitted_answers


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if not user.is_authenticated:
        return redirect('onlinecourse:login')

    if request.method == 'POST':
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        if not enrollment:
            enrollment = Enrollment.objects.create(user=user, course=course, mode='honor')
            course.total_enrollment += 1
            course.save()

        submission = Submission.objects.create(enrollment=enrollment)
        selected_ids = extract_answers(request)
        for choice_id in selected_ids:
            try:
                choice = Choice.objects.get(pk=choice_id)
                submission.choices.add(choice)
            except Choice.DoesNotExist:
                pass

        return HttpResponseRedirect(reverse('onlinecourse:show_exam_result', args=(course.id, submission.id)))

    return HttpResponseRedirect(reverse('onlinecourse:course_details', args=(course.id,)))


def show_exam_result(request, course_id, submission_id):
    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')

    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Security check: ensure student cannot access another student's exam results
    if submission.enrollment.user != request.user and not request.user.is_staff:
        return HttpResponseRedirect(reverse('onlinecourse:course_details', args=(course.id,)))

    context = {}
    context['course'] = course
    context['submission'] = submission

    # Extract selected choice IDs from submission
    selected_choice_ids = list(submission.choices.values_list('id', flat=True))
    context['selected_ids'] = selected_choice_ids

    total_score = 0
    total_possible = 0
    questions = course.question_set.all()
    if not questions.exists():
        questions = Question.objects.filter(lesson__course=course)

    for question in questions:
        total_possible += question.grade
        if question.is_get_score(selected_choice_ids):
            total_score += question.grade

    grade = int((total_score / total_possible) * 100) if total_possible > 0 else 0
    context['grade'] = grade
    context['total_score'] = total_score
    context['total_possible'] = total_possible

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)




