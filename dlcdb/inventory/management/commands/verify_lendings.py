from datetime import timedelta, date
from smtplib import SMTPException

from django.conf import settings
from django.core import mail
from django.core.validators import validate_email
from django.core.management.base import BaseCommand, CommandError

from django.template.loader import get_template
# from django.utils import timezone

from dlcdb.core.models import Inventory, Device, Person, Note, LentRecord


class Command(BaseCommand):
    help = 'Send emails (TO: lender, BCC: it-support) about all lented devices without an current inventory stamp or generate a report file.'

    MAILTO_KEYWORD_LENDER = "to_lender"
    SEPARATOR = 80 * "*"


    def add_arguments(self, parser):
        parser.add_argument(
            '--send_mails',
            action='store_true',
            help='Send mails. Defaults to False. If send_mails is true but no --mailto_addr is given, emails only get reported via console.',
        )
        parser.add_argument(
            '--mailto_addr',
            required=False,
            type=str,
            # default=settings.DEFAULT_FROM_EMAIL,
            help=f'Send verification emails to given email address. Defaults to `{settings.DEFAULT_FROM_EMAIL}`. Set to value `{self.MAILTO_KEYWORD_LENDER}` to mail actual lenders; or Set to value to a single email addr to send all emails to this given addr; or give a list of email addrs (format: `"receipient1@fqdn, receipient2@fqdn,...")` to only notifiy this given email addresses. Processed only when --send_mails is set.',
        )
        parser.add_argument(
            '--deadline_days_from_now',
            default=8,
            type=int,
            help=f'Deadline for answer emails in days from now. Defaults to `8`.',
        )


    def get_lenders_qs(self, devices_qs):
        lenders_pks = set(devices_qs.values_list('active_record__person__pk', flat=True))
        lenders_qs = Person.objects.filter(pk__in=lenders_pks).order_by("email")
        return lenders_qs


    def send_mails(self, devices=None, now=None, mailto_addr_arg=None, deadline_days=None):
        email_objs = []
        deadline = now + timedelta(days=deadline_days)

        for lender in self.get_lenders_qs(devices):
            lent_devices = devices.filter(active_record__person=lender).order_by("device_type")

            lender_email = None

            if lender.udb_person_email_internal_business:
                lender_email=lender.udb_person_email_internal_business
            elif lender.email:
                lender_email=lender.email
            elif lender.udb_person_email_private:
                lender_email=lender.udb_person_email_private

            if not lender_email:
                raise CommandError(f"No email address found for user {lender}. No emails sent. Exit!")

            recipient = self.get_recipient(lender_email=lender_email, mailto_addr=mailto_addr_arg)

            if recipient: 
                print(f"Preparing email. Lender: `{lender}`. Recipient: `{recipient}`. Devices: `{lent_devices.count()}`")
                email_obj = self.build_email_obj(
                    recipient=recipient,
                    person=lender,
                    devices=lent_devices,
                    deadline=deadline,
                )
                email_objs.append(email_obj)

        try:
            connection = mail.get_connection(fail_silently=False)
            messages = email_objs
            connection.send_messages(messages)
            self.stdout.write(f"+++ verify loaned equipment: {len(email_objs)} emails sent +++")
            self.stdout.write(f"Count lenders/emails: {self.get_lenders_qs(devices).count()}")
            self.stdout.write(f"Count devices:        {devices.count()}")
        except SMTPException as e:
            print(f"Mail Sending Failed! SMTPException was: '{e}'")


    def build_email_obj(self, person=None, recipient=None, devices=None, deadline=None):
        email_template_subject = get_template('inventory/email/verify_lendings_subject.txt')
        email_template_body = get_template('inventory/email/verify_lendings_body.txt')

        email_context = {
            'subject_prefix': settings.EMAIL_SUBJECT_PREFIX,
            'devices': devices,
            'person': person,
            'deadline': deadline,
            'contact_email': settings.DEFAULT_FROM_EMAIL,
        }
        subject = email_template_subject.render(email_context)
        body = email_template_body.render(email_context) 

        email_obj = mail.EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient], # expects a list
            cc=[settings.DEFAULT_FROM_EMAIL],
        )

        return email_obj


    def get_recipient(self, lender_email, mailto_addr):
        """
        To whom these emails should be sent?
        if cli arg --mailto_addr:
        = keyword 'to_lender' -> sent all emails directly to lenders
        = only one email addr -> sent all emails to this email addr istead of the lenders
        = list of email addrs -> send emails only to this subset of matching receipients email addrs
        """
        recipient = None
        mailto_addrs_list = mailto_addr.split(",")

        try:
            _validate_lender_email = validate_email(lender_email)
            _validate_mailto_addrs_list = map(validate_email, mailto_addrs_list)
        except:
            raise CommandError(f"Command error: `{recipient}` is not a valid email address! Exit!")

        try:
            if mailto_addr == self.MAILTO_KEYWORD_LENDER:
                recipient = lender_email
            elif len(mailto_addrs_list) == 1:
                recipient = mailto_addr
            elif len(mailto_addrs_list) >= 2:
                if lender_email in mailto_addrs_list:
                    recipient = lender_email
        except:
            raise CommandError(f"Command line arg `--mailto_addr {mailto_addr}` not valid! Exit!")

        return recipient


    def update_inventory_note(self, devices, inventory):
        """
        If a lender get an email, remember this via an inventory note.
        """
        print(f"{devices=}")
        lender_contacted_msg = f"Lender was contacted via email about the location of the device, so far without feedback."

        for device in devices:
            inventory_note_obj, inventory_note_obj_created = Note.objects.get_or_create(
                inventory=inventory,
                device=device,
            )
            # Append lender contacted msg to inventory note:
            inventory_note_obj.text = f"{inventory_note_obj.text}{'; ' if inventory_note_obj.text else ''}{lender_contacted_msg}"
            inventory_note_obj.save()


    def handle(self, *args, **options):
        # Command line args
        send_mails_arg = options['send_mails']
        mailto_addr_arg = options['mailto_addr'].replace(" ", "") if options['mailto_addr'] else None
        deadline_days_from_now_arg = options['deadline_days_from_now']

        print(self.SEPARATOR)
        print("Given command line arguments:")
        print(f"send_mails:                        {send_mails_arg}")  # type={type(send_mails_arg)}
        print(f"mailto_addr:                       {mailto_addr_arg}")  # type={type(mailto_addr_arg)}
        print(f"deadline_days_from_now:            {deadline_days_from_now_arg}")
        print(self.SEPARATOR)

        if not any([
            send_mails_arg,
            mailto_addr_arg,
        ]):
            self.stdout.write(f"+++ No action given on command line. Try `--help`. +++")
            return

        now = date.today()

        # Invocation of main methods:
        if send_mails_arg:
            mail_devices = Inventory.objects.lent_devices(
                exclude_already_inventorized=True,
            )

            if mailto_addr_arg:
                self.stdout.write("Will send mails...")
                self.send_mails(devices=mail_devices, now=now, mailto_addr_arg=mailto_addr_arg, deadline_days=deadline_days_from_now_arg)

                self.stdout.write("Add or update inventory notes...")
                current_inventory = Inventory.objects.active_inventory()
                self.update_inventory_note(mail_devices, current_inventory)
            else:
                lenders = mail_devices
                self.stdout.write(f"+++ No `--mail_addr` given, only report mailings +++")
                self.stdout.write(f"Count lenders/emails: {self.get_lenders_qs(mail_devices).count()}")
                self.stdout.write(f"Count devices:        {mail_devices.count()}")
