import re
import requests
import os
import re
import builtins
import pickle
import subprocess
import sys
from operator import itemgetter

from github3 import login
from tabulate import tabulate
from xonsh.built_ins import iglobpath
from xonsh.tools import subexpr_from_unbalanced
from xonsh.tools import ON_WINDOWS
from xonsh.environ import repo_from_remote


class GitSome(object):

    def __init__(self):
        get_env = lambda name, default=None: builtins.__xonsh_env__.get(
            name, default)
        self.user_id = get_env('GITHUB_USER_ID', None)
        self.user_pass = get_env('GITHUB_USER_PASS', None)
        self.token = get_env('GITHUB_TOKEN', None)
        if self.token is not None:
            self.gh = login(token=self.token,
                            two_factor_callback=self._two_factor_code)
            print('Authenticated with token:', self.gh.me().login)
        else:
            self.gh = login(self.user_id,
                            self.user_pass,
                            two_factor_callback=self._two_factor_code)
            print('Authenticated with user id and password', self.gh.me().login)
        self.repo = repo_from_remote()
        self.rate_limit()
        self.dispatch = {
            'emails': self.emails,
            'emojis': self.emojis,
            'events': self.events,
            'feeds': self.feeds,
            'followers': self.followers,
            'following': self.following,
            'gitignore_template': self.gitignore_template,
            'gitignore_templates': self.gitignore_templates,
            'issue': self.issue,
            'issues': self.issues,
            'me': self.me,
            'notifications': self.notifications,
            'octocat': self.octocat,
            'pull_requests': self.pull_requests,
            'rate_limit': self.rate_limit,
            'repo': self.repo,
            'repos': self.repos,
            'search_issues': self.search_issues,
            'search_repositories': self.search_repositories,
            'stars': self.stars,
        }

    def _two_factor_code(self):
        code = ''
        while not code:
            code = input('Enter 2FA code: ')
        return code

    def _return_elem_or_list(self, args):
        if len(args) == 1:
            return args[0]
        else:
            return args

    def _extract_args(self,
                      input_args,
                      default_args,
                      expected_args):
        # If we don't have input args, use the default args if they exist
        if not input_args and default_args is not None:
            return self._return_elem_or_list(default_args)
        valid_args = True
        # If we expect args and the we don't get any args or
        # if the number of input args doesn't match the number of expected args
        if (expected_args is not None and input_args is None) or \
            len(input_args) != len(expected_args):
            valid_args = False
        if not valid_args:
            print('Error, expected arguments:', expected_args)
            return None
        else:
            # All checks pass on the input args for use
            return self._return_elem_or_list(input_args)
        return None

    def _format_repo(self, repo):
        return '/'.join(repo)

    def _listify(self, items):
        output = []
        for item in items:
            item_list = []
            item_list.append(item)
            output.append(item_list)
        return output

    def _print_items(self, items, headers):
        table = []
        for item in items:
            table.append(item)
        self._print_table(table, headers=headers)

    def _print_table(self, table, headers):
        print(tabulate(table, headers, tablefmt='grid'))

    def emails(self, _):
        self._print_items(self.gh.emails(), headers='keys')

    def emojis(self, _):
        self._print_items(self._listify(self.gh.emojis()), headers=['emoji'])

    def events(self, _):
        events = self.gh.all_events()
        table = []
        for event in events:
            table.append([event.created_at,
                          event.actor,
                          event.type,
                          self._format_repo(event.repo)])
        self._print_table(table,
                          headers=['created at', 'user', 'type', 'repo'])

    def execute(self, args):
        if args:
            self.repo = user_and_repo_from_path()
            command = args[0]
            command_args = args[1:] if args[1:] else None
            self.dispatch[command](command_args)
            rate_limit_print_threshold = 20
            self.rate_limit([rate_limit_print_threshold])
        else:
            print("Available commands for 'gh':")
            self._print_items(
                self._listify(self.dispatch.keys()),
                headers=['command'])

    def feeds(self, _):
        self.gh.feeds()

    def followers(self, args):
        user = self._extract_args(
            args,
            default_args=[self.user_id],
            expected_args=['user'])
        self._print_items(
            self._listify(self.gh.followers_of(user)), headers=['user'])
        print('Followers:', self.gh.user(user).followers_count)

    def following(self, args):
        user = self._extract_args(
            args,
            default_args=[self.user_id],
            expected_args=['user'])
        self._print_items(
            self._listify(self.gh.followed_by(user)), headers=['user'])
        print('Following:', self.gh.user(user).followers_count)

    def gitignore_template(self, args):
        language = self._extract_args(
            args,
            default_args=None,
            expected_args=['language'])
        template = self.gh.gitignore_template(language)
        if template != '':
            print(template)
        else:
            print('Invalid template requested, run the following command to' \
                  ' see available templates:\n    gh gitignore_templates')

    def gitignore_templates(self, args):
        self._print_items(
            self._listify(self.gh.gitignore_templates()), headers=['language'])

    def issue(self, args):
        result = self._extract_args(
            args,
            default_args=None,
            expected_args=['user', 'repo', 'issue #'])
        if result is None:
            return
        user, repo, issue_number = result
        issue = self.gh.issue(user, repo, issue_number)
        if type(issue) is null.NullObject:
            print('Error: Invalid issue.')
            return
        print('repo:', self._format_repo(issue.repository))
        print('title:', issue.title)
        print('issue url:', issue.html_url)
        print('issue number:', issue.number)
        print('state:', issue.state)
        print('comments:', issue.comments_count)
        print('labels:', issue.original_labels)
        print('milestone:', issue.milestone)
        print('')
        print(issue.body)
        comments = issue.comments()
        for comment in comments:
            print('')
            print('---Comment---')
            print('')
            print('user:', comment.user)
            print('comment url:', comment.html_url)
            print('created at:', comment.created_at)
            print('updated at:', comment.updated_at)
            print('')
            print(comment.body)

    def issues(self, args):
        issue_filter = self._extract_args(
            args,
            default_args=['subscribed'],
            expected_args=["'assigned', 'created', 'mentioned', 'subscribed'"])
        issues = self.gh.issues(filter=issue_filter)
        table = []
        for issue in issues:
            table.append([issue.number,
                          self._format_repo(issue.repository),
                          issue.title,
                          issue.comments_count])
        table = sorted(table, key=itemgetter(1, 0))
        self._print_table(table,
                          headers=['#', 'repo', 'title', 'comments'])

    def me(self, _):
        user = self.gh.me()
        print(user.login)
        if user.company is not None:
            print('company:', user.company)
        if user.location is not None:
            print('location:', user.location)
        if user.email is not None:
            print('email:', user.email)
        print('joined on:', user.created_at)
        print('followers:', user.followers_count)
        print('following:', user.following_count)
        self.repos(args=None)

    def notifications(self, args):
        import pdb; pdb.set_trace()
        notifs = self.gh.notifications(participating=True)
        self._print_items(self.gh.notifications(participating=True),
                          headers=['foo'])

    def octocat(self, args):
        say = self._extract_args(
            args,
            default_args=[''],
            expected_args=['say'])
        output = str(self.gh.octocat(say))
        output = output.replace('\\n', '\n')
        print(output)

    def rate_limit(self, args=None):
        threshold = self._extract_args(
            args,
            default_args=[sys.maxsize],
            expected_args=['threshold'])
        limit = self.gh.ratelimit_remaining
        if limit < threshold:
            print('Rate limit:', limit)

    def repo(self, args):
        user, repo = self._extract_args(
            args,
            default_args=[self.user_id, self.repo],
            expected_args=['user', 'repo'])
        repository = self.gh.repository(user, repo)
        print('description:', repository.description)
        print('stars:', repository.stargazers_count)
        print('forks:', repository.forks_count)
        print('created at:', repository.created_at)
        print('updated at:', repository.updated_at)
        print('clone url:', repository.clone_url)

    def repos(self, _):
        repos = self.gh.repositories()
        table = []
        for repo in repos:
            table.append([repo.name, repo.stargazers_count])
        table = sorted(table, key=itemgetter(1, 0), reverse=True)
        print(tabulate(table, headers=['repo', 'stars'], tablefmt='grid'))

    def search_issues(self, args):
        query = self._extract_args(
            args,
            default_args=[None],
            expected_args=['query'])
        issues = self.gh.search_issues(query)
        table = []
        try:
            for issue in issues:
                table.append([issue.score,
                             issue.issue.number,
                             self._format_repo(issue.issue.repository),
                             issue.issue.title])
        except AttributeError:
            # github3.py sometimes throws the following during iteration:
            # AttributeError: 'NoneType' object has no attribute 'get'
            pass
        # Sort by score, repo, issue number
        table = sorted(table, key=itemgetter(0, 2, 1), reverse=True)
        self._print_table(table, headers=['score', '#', 'repo', 'title'])

    def search_repositories(self, args):
        query = self._extract_args(
            args,
            default_args=[None],
            expected_args=['query'])
        repos = self.gh.search_repositories(query)
        table = []
        try:
            for repo in repos:
                table.append([repo.score,
                              repo.repository.full_name,
                              repo.repository.stargazers_count,
                              repo.repository.forks_count])
        except AttributeError:
            # github3.py sometimes throws the following during iteration:
            # AttributeError: 'NoneType' object has no attribute 'get'
            pass
        # Sort by score, repo
        table = sorted(table, key=itemgetter(0, 1), reverse=True)
        self._print_table(table, headers=['score', 'repo', 'stars', 'forks'])

    def stars(self, args):
        user, repo = self._extract_args(
            args,
            default_args=[self.user_id, self.repo],
            expected_args=['user', 'repo'])
        stars = str(self.gh.repository(user, repo).stargazers_count)
        print('Stars for ' + user + '/' + repo + ': ' + stars)
