from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from conferences.models import Conference, ConferenceProposalReviewer
from proposals.forms import ProposalForm, ProposalCommentForm
from proposals.models import Proposal, ProposalComment


def _is_proposal_author(user, proposal):
    if user.is_authenticated() and proposal.author == user:
        return True
    return False


def _is_proposal_reviewer(user, proposal):
    if user.is_authenticated() and ConferenceProposalReviewer.objects.filter(reviewer=user, active=True):
        return True
    return False


def _is_proposal_author_or_reviewer(user, proposal):
    return _is_proposal_author(user, proposal) or _is_proposal_reviewer(user, proposal)


@require_http_methods(['GET'])
def list_proposals(request, conference_slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    proposals_list = Proposal.objects.filter(conference=conference)
    return render(request, 'proposals/list.html', {'proposals_list': proposals_list,
                                                   'conference': conference})


@login_required
@require_http_methods(['GET', 'POST'])
def create_proposal(request, conference_slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    if request.method == 'GET':
        form = ProposalForm(conference)
        return render(request, 'proposals/create.html', {'form': form})

    # POST Workflow
    form = ProposalForm(conference, request.POST)

    if not form.is_valid():
        return render(request, 'proposals/create.html', {'form': form,
                                                         'conference': conference,
                                                         'errors': form.errors})

    # Valid Form
    Proposal.objects.create(author=request.user,
                            conference=conference,
                            title=form.cleaned_data['title'],
                            description=form.cleaned_data['description'],
                            target_audience=form.cleaned_data[
                                'target_audience'],
                            prerequisites=form.cleaned_data['prerequisites'],
                            content_urls=form.cleaned_data['content_urls'],
                            speaker_info=form.cleaned_data['speaker_info'],
                            speaker_links=form.cleaned_data['speaker_links'],
                            status=form.cleaned_data['status'],
                            proposal_type_id=form.cleaned_data[
                                'proposal_type'],
                            proposal_section_id=form.cleaned_data[
                                'proposal_section']
                            )

    return HttpResponseRedirect(reverse('proposals-list',
                                        args=[conference.slug]))


@require_http_methods(['GET'])
def detail_proposal(request, conference_slug, slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    proposal = get_object_or_404(Proposal, slug=slug, conference=conference)
    allow_private_comment = _is_proposal_author_or_reviewer(request.user, proposal)

    comments = ProposalComment.objects.filter(proposal=proposal)
    if not allow_private_comment:
        comments = comments.filter(private=False)

    proposal_comment_form = ProposalCommentForm()

    if request.user == proposal.author:
        return render(request, 'proposals/detail.html', {'proposal': proposal,
                                                         'comments': comments,
                                                         'proposal_comment_form': proposal_comment_form,
                                                         'allow_private_comment': allow_private_comment,
                                                         'can_delete': True})

    return render(request, 'proposals/detail.html', {'proposal': proposal,
                                                     'comments': comments,
                                                     'proposal_comment_form': proposal_comment_form,
                                                     'allow_private_comment': allow_private_comment,
                                                     'can_delete': False})


@login_required
@require_http_methods(['GET', 'POST'])
def update_proposal(request, conference_slug, slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    proposal = get_object_or_404(Proposal, slug=slug, conference=conference)

    if not proposal.author == request.user:
        return HttpResponseForbidden()

    if request.method == 'GET':
        form = ProposalForm.populate_form_for_update(proposal)
        return render(request, 'proposals/update.html', {'form': form})

    # POST Workflow
    form = ProposalForm(conference, request.POST)
    if not form.is_valid():
        return render(request, 'proposals/update.html', {'form': form,
                                                         'errors': form.errors})

    # Valid Form
    proposal.title = form.cleaned_data['title']
    proposal.description = form.cleaned_data['description']
    proposal.target_audience = form.cleaned_data['target_audience']
    proposal.prerequisites = form.cleaned_data['prerequisites']
    proposal.content_urls = form.cleaned_data['content_urls']
    proposal.speaker_info = form.cleaned_data['speaker_info']
    proposal.speaker_links = form.cleaned_data['speaker_links']
    proposal.status = form.cleaned_data['status']
    proposal.proposal_type_id = form.cleaned_data['proposal_type']
    proposal.proposal_section_id = form.cleaned_data['proposal_section']
    proposal.save()
    return HttpResponseRedirect(reverse('proposals-list',
                                        args=[conference.slug]))


@login_required
@require_http_methods(['GET', 'POST'])
def delete_proposal(request, conference_slug, slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    proposal = get_object_or_404(Proposal, slug=slug, conference=conference)

    if not proposal.author == request.user:
        return HttpResponseForbidden()

    if request.method == 'GET':
        return render(request, 'proposals/delete.html', {'proposal': proposal})
    elif request.method == 'POST':
        proposal.delete()
        return HttpResponseRedirect(reverse('proposals-list',
                                            args=[conference.slug]))


@login_required
@require_http_methods(['POST'])
def create_proposal_comment(request, conference_slug, proposal_slug):
    conference = get_object_or_404(Conference, slug=conference_slug)
    proposal = get_object_or_404(Proposal, slug=proposal_slug, conference=conference)

    form = ProposalCommentForm(request.POST)
    if form.is_valid():
        comment = form.cleaned_data['comment']
        private = form.cleaned_data['private']

        ProposalComment.objects.create(proposal=proposal,
                                       comment=comment,
                                       private=private,
                                       commenter=request.user,
                                       )

    return HttpResponseRedirect(reverse('proposal-detail',
                                        args=[conference.slug, proposal.slug]))