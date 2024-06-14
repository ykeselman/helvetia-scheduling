TAG = 'tag'
SUBJECT = 'subject'
MESSAGE = 'message'

SUBJECT_FR = 'subject_fr'

NOT_FOUND = 'not found'
CONFIRMED = 'confirmed'
TEST_INVITE = 'test_invite'

MESSAGES = [
  {
    TAG: NOT_FOUND,
    SUBJECT: "Helvetia Connect – Your email was not found in our system",
    MESSAGE: """
Hello,

We apologize for the inconvenience, but the email you indicated {email} was not found in our system.

If you are already a Connect user, please try again with the email address you have used to create
your account with us.

If you are not yet a Connect user, please visit this page https://helvetiaconnect.ch/en/faculty to register.

Thank you,

The Helvetia Connect Team

""" + (80 * '-') + """

Bonjour

Nous vous prions de nous excuser pour la gêne occasionnée, mais le courriel que vous avez indiqué {email}
n’a pas été trouvé dans notre système.

Si vous êtes déjà un utilisateur Connect, veuillez réessayer avec l’adresse e-mail que vous avez utilisée
pour créer votre compte chez nous.

Si vous n’êtes pas encore un utilisateur Connect, veuillez visiter cette page
https://helvetiaconnect.ch/fr/faculty-fr pour vous inscrire.

Bien à vous,

Votre Équipe Helvetia Connect
"""
  },

  {
    TAG: CONFIRMED,
    SUBJECT: "Helvetia Connect – Your scheduling information is confirmed",
    SUBJECT_FR: "Helvetia Connect – Vos informations de planification sont confirmées",
    MESSAGE: """
Dear {first_name},

Thank you for sending us your availabilities. This is a confirmation that we have received them,
and they will be used for subsequent scheduling and job bookings.

Please remember to keep those availabilities up to date, as to allow the operations to run as smoothly as possible.

Kind regards,

Your Helvetia Connect Team

""" + (80 * '-') + """

Bonjour {first_name},

Merci de nous avoir envoyé vos disponibilités. Ceci est une confirmation que nous les avons reçues, et elles seront
utilisées pour la planification et les réservations de jobs ultérieures.

N’oubliez pas de tenir ces disponibilités à jour, afin que l’opérationnel puisse se dérouler le mieux possible.

Bien à vous,

Votre Équipe Helvetia Connect
"""
  },

  {
    TAG: TEST_INVITE,
    SUBJECT: "User {email} is available",
    MESSAGE: "User {email} is available for scheduling"
  }
]
