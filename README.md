# Django - Check SSL Expiration
# Introduction
> This is an Django application which checks 
>SSL expiration of host if host is has less than 15 days of 
>SSL Expiration means a message will be sended from sender email to all receiver emails else it will show None of the host has less 
>than 15 days of SSL expiration.
## Getting Started

### Prerequisites
To send email user should enable less secure apps and imap
- [Python 3.5+]()
- [To send mail - Enable Less Secure Apps](https://myaccount.google.com/lesssecureapps)
- [Enable IMAP](https://mail.google.com/mail/u/0/?tab=rm&ogbl#settings/fwdandpop)
Note : Here we used gmail for sending the mails


## Setup

The first thing to do is to clone the repository:

```sh
$ git clone https://github.com/gocardless/sample-django-app.git
```

Create and activate a virtualenv:

```bash
virtualenv venv
source venv/bin/activate 
```

Then install the dependencies:

```sh
(env)$ pip install -r requirements.txt

Once `pip` has finished downloading the dependencies:
```sh
(venv)$ python manage.py runserver
```

Configure the SSL/settings.py
```sh
EMAIL_HOST_USER =  'Add sender email'
EMAIL_HOST_PASSWORD =  'Add password'
```

Configure the SSL/template/index.html
```sh
Add sender email in input field to denote that we are using it only to send emails(read only)
```


And navigate to `http://127.0.0.1:8000/`.