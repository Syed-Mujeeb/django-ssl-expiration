from django.shortcuts import render,redirect,HttpResponse
from django.core.mail import send_mail,EmailMessage
from django.conf import settings
from django.contrib import messages

from cryptography import x509
from cryptography.x509.oid import NameOID
from socket import socket
from collections import namedtuple
from OpenSSL import *
import re
import datetime
import concurrent.futures
import idna

HostInfo = namedtuple(field_names='cert hostname peername', typename='HostInfo')

def get_certificate(hostname, port):
    hostname_idna = idna.encode(hostname)
    sock = socket()
    sock.connect((hostname, port))
    peername = sock.getpeername()
    ctx = SSL.Context(SSL.SSLv23_METHOD)  # most compatible
    ctx.check_hostname = False
    ctx.verify_mode = SSL.VERIFY_NONE
    sock_ssl = SSL.Connection(ctx, sock)
    sock_ssl.set_connect_state()
    sock_ssl.set_tlsext_host_name(hostname_idna)
    sock_ssl.do_handshake()
    cert = sock_ssl.get_peer_certificate()
    crypto_cert = cert.to_cryptography()
    sock_ssl.close()
    sock.close()
    return HostInfo(cert=crypto_cert, peername=peername, hostname=hostname)

def get_alt_names(cert):
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return ext.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        return None

def get_common_name(cert):
    try:
        names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value
    except x509.ExtensionNotFound:
        return None

def get_issuer(cert):
    try:
        names = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value
    except x509.ExtensionNotFound:
        return None

def print_basic_info(hostinfo):
    str = '''» {hostname} « … {peername}
    \tcommonName: {commonname}
    \tSAN: {SAN}
    \tissuer: {issuer}
    \tnotBefore: {notbefore}
    \tnotAfter:  {notafter}
    '''.format(
        hostname=hostinfo.hostname,
        peername=hostinfo.peername,
        commonname=get_common_name(hostinfo.cert),
        SAN=get_alt_names(hostinfo.cert),
        issuer=get_issuer(hostinfo.cert),
        notbefore=hostinfo.cert.not_valid_before,
        notafter=hostinfo.cert.not_valid_after
    )

    s=[]
    s.append(hostinfo.hostname)
    s.append(hostinfo.peername)
    s.append(get_common_name(hostinfo.cert))
    s.append(get_alt_names(hostinfo.cert))
    s.append(get_alt_names(hostinfo.cert))
    s.append(get_issuer(hostinfo.cert))
    s.append(hostinfo.cert.not_valid_before)
    s.append(hostinfo.cert.not_valid_after)
    return (str,s)

def check_it_out(hostname, port):
    hostinfo = get_certificate(hostname, port)
    print_basic_info(hostinfo)

# Create your views here.


def index(request):
    URL = 'sslapp/index.html'
    regex_for_email = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$' # using this to validate email address
    RET_HOST = '' # if host is not found then error message is been sent using this variable
    RET_REMAIL = ''  # if receiver email is not found then error message is been sent using this variable
    HOST_LIST = [] # Contains list of host
    send = 1   #If receiver email is not valid,Then message will not be sended
    expiry_count = 0 #
    Host_with_expiry_date = {}

    td=datetime.datetime.today().replace(microsecond=0)
    if (request.method == "POST"):
        sender_email = settings.EMAIL_HOST_USER
        receiver_email = request.POST['r_email']
        receiver_email = "".join(receiver_email.split())
        receiver_email_list = receiver_email.split(',')
        receiver_email_list = [ i for i in receiver_email_list if i]
        for email in receiver_email_list:
            if (re.search(regex_for_email , email)) :
                pass
            else:
                RET_REMAIL = request.POST['r_email']
                RET_HOST = request.POST['host']
                messages.error(request , str(email) + " - Receiver email address is incorrect")
                send = 0
                break

        if(send == 0): #If email id is not valid then we are raising error and not redirecting to result page
            pass
        else:
            HOST = request.POST['host']
            HOST="".join(HOST.split())
            TEMP_LIST = list(HOST.split(','))
            print(TEMP_LIST)
            TEMP_LIST = [i for i in TEMP_LIST if i]
            length = len(TEMP_LIST)
            for i in range(0 , length) :
                HOST_LIST.append((TEMP_LIST[i] , 443))

            subject = 'SSL_Expiration'
            recipient_list = receiver_email_list
            message = ''
            with concurrent.futures.ThreadPoolExecutor(max_workers = 4) as e :
                counter = 1
                HOST_NOT_FOUND = 0
                try :
                    for hostinfo in e.map(lambda x : get_certificate(x[0] , x[1]) , HOST_LIST) :
                        ssl_expire , s = print_basic_info(hostinfo)
                        str_ssl_expire = s[-1]
                        delta = str_ssl_expire - td
                        Host_with_expiry_date[s[0]] = delta.days
                        HOST_NOT_FOUND += 1
                        if (delta.days >= 15) : #Message will be send only when expiration days is less than or equal to 15
                            # and send = 1
                            body = str(counter) + ". " + str(s[0]) + ' Going to expire in ' + str(
                                delta.days) + ' days \r'
                            message = message + body
                            counter += 1
                            expiry_count+=1
                            send = 1


                        else:
                            send =2 # Message will not be send . This denotes that none of the host has <=15 days of expiration
                except :
                    RET_REMAIL = request.POST['r_email']
                    RET_HOST = request.POST['host']
                    messages.error(request ,  str(HOST_LIST[HOST_NOT_FOUND][0]) + " - Host name is incorrect")
                    send=0

                request.session['send'] = send
                request.session['expiry_count'] =expiry_count
                Host_with_expiry_date = sorted(Host_with_expiry_date.items() , key = lambda expiry : expiry[1])
                request.session['Host_with_expiry_date'] = Host_with_expiry_date

                if(send==1):
                    send_mail(subject,message,sender_email,receiver_email_list)
                    return redirect('/result')
                elif(send == 2):
                    return redirect('/result')

    return render(request , URL , {'RET_HOST' : RET_HOST,'RET_REMAIL': RET_REMAIL})

def result(request):
    URL= 'sslapp/result.html'
    Host_table = request.session.get('Host_with_expiry_date')
    Message_Sent = request.session.get('send')
    Expiry_Count = request.session.get('expiry_count')
    if Message_Sent == 1:
        messages.success(request,"Message Sent : Found "+ str(Expiry_Count) +" host that going to expire within 15 days")
    else:
        messages.info(request,"None of the host has less than 15 days of ssl expiration")

    return render(request,URL,{'Host_table' : Host_table})










