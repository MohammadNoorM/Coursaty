"""Seed the database with a full set of bilingual demo data.

WARNING: by default this command FLUSHES THE ENTIRE DATABASE before
seeding. It is meant for demo/staging environments, not production
databases with real user data.

The seed creates:

- 1 admin superuser (random password, printed once) plus 3 instructors
  and 14 demo students (shared demo password, printed once)
- 6 bilingual categories
- 63 bilingual courses (3 deliberately unpublished) with thumbnails
  uploaded from a local images folder
- 4 sections x 5 lessons per course (~1,260 lessons) whose videos
  reference the files already hosted on Cloudinary
- Enrollments, payments, ratings, threaded comments and wishlists
- 11 blog posts (alternating English/Arabic) with cover images

Lesson videos are taken from the existing database references (or, on
an empty database, from the Cloudinary ``courses/videos/`` folder) and
are never re-uploaded or deleted.

Usage::

    python manage.py seed_demo --images /path/to/images
        [--admin-password SECRET] [--skip-wipe] [--cleanup-media]
"""

import itertools
import random
import secrets
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone, translation

from blog.models import Post
from courses.models import (Category, Comment, Course, Enrollment, Lesson,
                            Rating, Section, Wishlist, custom_slugify)
from payments.models import Payment

random.seed(42)  # reproducible demo data

DEMO_STUDENT_PASSWORD = "CoursatyDemo!2026"

PRICES = [Decimal(p) for p in
          ("19.99", "24.99", "29.99", "39.99", "49.99", "59.99", "79.99", "99.99")]

# (key, English name, Arabic name)
CATEGORIES = [
    ("web", "Web Development", "تطوير الويب"),
    ("prog", "Programming Languages", "لغات البرمجة"),
    ("ai", "AI & Data Science", "الذكاء الاصطناعي وعلوم البيانات"),
    ("design", "UI/UX Design", "تصميم واجهات وتجربة المستخدم"),
    ("business", "Business & Product", "الأعمال وإدارة المنتجات"),
    ("cs", "Computer Science", "علوم الحاسوب"),
]

# (English title, Arabic title) per category key; 63 courses in total.
COURSES = {
    "web": [
        ("HTML & CSS Fundamentals", "أساسيات HTML و CSS"),
        ("Responsive Web Design", "تصميم الويب المتجاوب"),
        ("JavaScript Essentials", "أساسيات جافاسكريبت"),
        ("Modern React From the Ground Up", "تطوير تطبيقات React الحديثة"),
        ("Build Web Apps with Django", "بناء تطبيقات الويب باستخدام Django"),
        ("REST APIs with Django REST Framework", "بناء واجهات REST باستخدام Django"),
        ("Tailwind CSS From Scratch", "تعلم Tailwind CSS من الصفر"),
        ("Node.js & Express Fundamentals", "أساسيات Node.js و Express"),
        ("Databases & SQL for Web Developers", "قواعد البيانات و SQL لمطوري الويب"),
        ("Web Performance Optimization", "تحسين أداء مواقع الويب"),
        ("Full-Stack Project: Ship Your First App", "مشروع متكامل: انشر أول تطبيق لك"),
    ],
    "prog": [
        ("Python Programming for Beginners", "تعلم برمجة بايثون للمبتدئين"),
        ("Advanced Python Patterns", "أنماط بايثون المتقدمة"),
        ("PHP From Scratch", "تعلم PHP من الصفر"),
        ("Object-Oriented PHP", "البرمجة الكائنية بلغة PHP"),
        ("Ruby Fundamentals", "أساسيات لغة Ruby"),
        ("Ruby on Rails Basics", "أساسيات Ruby on Rails"),
        ("Clean Code Practices", "ممارسات كتابة الكود النظيف"),
        ("Git & Version Control Mastery", "احتراف Git وإدارة الإصدارات"),
        ("Algorithms & Problem Solving", "الخوارزميات وحل المشكلات"),
        ("Regular Expressions Deep Dive", "التعبيرات النمطية بعمق"),
    ],
    "ai": [
        ("Introduction to Artificial Intelligence", "مقدمة في الذكاء الاصطناعي"),
        ("Machine Learning Foundations", "أساسيات تعلم الآلة"),
        ("Deep Learning with Neural Networks", "التعلم العميق والشبكات العصبية"),
        ("Natural Language Processing Essentials", "أساسيات معالجة اللغات الطبيعية"),
        ("Computer Vision Fundamentals", "أساسيات الرؤية الحاسوبية"),
        ("Data Analysis with Python", "تحليل البيانات باستخدام بايثون"),
        ("Data Visualization & Storytelling", "سرد القصص بالبيانات المرئية"),
        ("Large Language Models in Practice", "النماذج اللغوية الكبيرة في الممارسة"),
        ("Prompt Engineering for Developers", "هندسة الأوامر للمطورين"),
        ("MLOps: Machine Learning in Production", "MLOps: تشغيل تعلم الآلة في الإنتاج"),
        ("Ethics & Responsible AI", "أخلاقيات الذكاء الاصطناعي"),
    ],
    "design": [
        ("UI Design Fundamentals", "أساسيات تصميم واجهات المستخدم"),
        ("UX Research Methods", "أساليب بحث تجربة المستخدم"),
        ("Design Systems in Practice", "أنظمة التصميم في الممارسة"),
        ("Figma Mastery", "احتراف Figma"),
        ("Mobile-First Design", "التصميم للهواتف أولًا"),
        ("Accessibility by Design", "التصميم الميسّر للجميع"),
        ("Prototyping & Micro-interactions", "النماذج الأولية والتفاعلات الدقيقة"),
        ("Color Theory & Typography", "نظرية الألوان وعلم الخطوط"),
        ("Web Animation for Designers", "حركة الويب للمصممين"),
        ("Building a Design Portfolio", "بناء معرض أعمال المصممين"),
    ],
    "business": [
        ("Product Management Essentials", "أساسيات إدارة المنتجات"),
        ("Agile & Scrum in Practice", "Agile و Scrum في الممارسة"),
        ("Digital Marketing Foundations", "أساسيات التسويق الرقمي"),
        ("Startup Finance Basics", "أساسيات التمويل للشركات الناشئة"),
        ("Data-Driven Decision Making", "اتخاذ القرارات المبنية على البيانات"),
        ("Stakeholder Communication", "التواصل مع أصحاب المصلحة"),
        ("Roadmapping & Strategy", "تخطيط الطريق والاستراتيجية"),
        ("Customer Discovery Interviews", "مقابلات استكشاف العملاء"),
        ("Growth Marketing Tactics", "تكتيكات التسويق للنمو"),
        ("Leadership for New Managers", "القيادة للمدراء الجدد"),
    ],
    "cs": [
        ("Computer Science 101", "مدخل إلى علوم الحاسوب"),
        ("Data Structures in Depth", "هياكل البيانات بعمق"),
        ("Algorithms: Sorting & Searching", "الخوارزميات: الترتيب والبحث"),
        ("Operating Systems Concepts", "مفاهيم أنظمة التشغيل"),
        ("Computer Networks Fundamentals", "أساسيات شبكات الحاسوب"),
        ("Databases & Data Modeling", "قواعد البيانات ونمذجة البيانات"),
        ("Compilers & Interpreters", "المترجمات والمفسرات"),
        ("Discrete Mathematics for CS", "الرياضيات المتقطعة لعلوم الحاسوب"),
        ("Cybersecurity Fundamentals", "أساسيات الأمن السيبراني"),
        ("Cloud Computing Essentials", "أساسيات الحوسبة السحابية"),
        ("Distributed Systems Basics", "مقدمة في الأنظمة الموزعة"),
    ],
}

SHORT_DESC_EN = [
    "Learn {t} step by step with hands-on projects and real-world examples.",
    "A practical, project-based course that takes you from zero to confident in {t}.",
    "Master {t} through bite-sized lessons, exercises, and a guided capstone project.",
    "Everything you need to get productive with {t}, taught with clarity and depth.",
]
SHORT_DESC_AR = [
    "تعلّم {t} خطوة بخطوة من خلال مشاريع عملية وأمثلة واقعية.",
    "دورة عملية قائمة على المشاريع تنقلك من الصفر إلى الثقة في {t}.",
    "أتقن {t} عبر دروس قصيرة وتمارين تطبيقية ومشروع تخرج موجّه.",
    "كل ما تحتاجه للإنتاجية في {t}، مشروحًا بوضوح وعمق.",
]

DESC_EN = [
    "{t} is one of the most in-demand skills in {c} today. This course builds a strong mental model of the fundamentals, then immediately puts them to work through guided exercises and realistic projects.\n\nBy the end you will have shipped a portfolio-worthy project, built the habits professionals rely on, and know exactly what to learn next.",
    "A practical, project-driven introduction to {t}. Every concept is introduced with a concrete example, practiced in a short exercise, and revisited in a larger project so it actually sticks.\n\nNo fluff and no filler: just the concepts, patterns, and workflows that working practitioners use every day, explained clearly and in context.",
]
DESC_AR = [
    "يُعد {t} من أكثر المهارات طلبًا في مجال {c} اليوم. تبني هذه الدورة فهمًا عميقًا للأساسيات ثم تضعها موضع التطبيق مباشرة من خلال تمارين موجّهة ومشاريع واقعية.\n\nستكون بنهاية الدورة قد أنجزت مشروعًا يستحق الإضافة إلى معرض أعمالك، واكتسبت عادات المحترفين، وعرفت بالضبط ما يجب تعلمه بعد ذلك.",
    "مقدمة عملية قائمة على المشاريع إلى {t}. كل مفهوم يُقدَّم بمثال ملموس، ويُمارَس في تمرين قصير، ثم يُعاد زيارته في مشروع أكبر حتى يترسخ فعلًا.\n\nبلا حشو ولا إطالة: المفاهيم والأنماط وأساليب العمل التي يستخدمها المحترفون يوميًا، مشروحةً بوضوح وسياق.",
]

WHAT_YOU_LEARN_EN = [
    "- Understand the core concepts of {t}\n- Build a complete, portfolio-worthy project\n- Apply professional best practices and patterns\n- Debug problems confidently on your own\n- Know exactly what to learn next",
    "- Set up a modern workflow for {t}\n- Master the fundamentals through hands-on exercises\n- Complete a guided real-world project\n- Read and reason about real-world tools and code\n- Develop habits of continuous learning",
]
WHAT_YOU_LEARN_AR = [
    "- فهم المفاهيم الأساسية في {t}\n- بناء مشروع كامل يستحق معرض أعمالك\n- تطبيق أفضل الممارسات والأنماط الاحترافية\n- تصحيح الأخطاء بثقة وباستقلالية\n- معرفة ما يجب تعلمه بعد ذلك بالضبط",
    "- تجهيز بيئة عمل حديثة لـ {t}\n- إتقان الأساسيات عبر تمارين عملية\n- إنجاز مشروع واقعي موجّه\n- قراءة وفهم الأدوات والأكواد الواقعية\n- تنمية عادات التعلم المستمر",
]

REQUIREMENTS_EN = [
    "- A computer with internet access\n- No prior experience needed, we start from the basics\n- Curiosity and a willingness to practice",
    "- Basic computer literacy\n- No background in {c} required\n- A few hours per week to practice",
]
REQUIREMENTS_AR = [
    "- حاسوب متصل بالإنترنت\n- لا تحتاج إلى خبرة سابقة، نبدأ من الأساسيات\n- الفضول والاستعداد للممارسة",
    "- معرفة أساسية باستخدام الحاسوب\n- لا تُطلب خلفية في {c}\n- بضع ساعات أسبوعيًا للممارسة",
]

# Four section titles per course, with an Arabic variant per archetype.
SECTION_ARCHETYPES = [
    (["Getting Started", "Core Concepts", "Hands-On Practice", "Capstone Project"],
     ["البداية", "المفاهيم الأساسية", "التطبيق العملي", "مشروع التخرج"]),
    (["Foundations", "Deep Dive", "Real-World Applications", "Review & Next Steps"],
     ["الأساسيات", "تعمّق في الموضوع", "تطبيقات واقعية", "المراجعة والخطوات التالية"]),
    (["Orientation", "Building Blocks", "Guided Projects", "Masterclass"],
     ["التعريف بالدورة", "لبنات البناء", "مشاريع موجّهة", "درس متقدم"]),
]

# Five lesson titles per section position (0..3), English and Arabic.
LESSON_TEMPLATES = [
    [
        ("{t}: Course Overview", "{t}: نظرة عامة على الدورة"),
        ("{t}: Setting Up Your Environment", "{t}: تجهيز بيئة العمل"),
        ("{t}: Core Concepts Explained", "{t}: شرح المفاهيم الأساسية"),
        ("{t}: Worked Examples", "{t}: أمثلة محلولة"),
        ("{t}: Practice Exercises", "{t}: تمارين تطبيقية"),
    ],
    [
        ("{t}: Advanced Techniques", "{t}: تقنيات متقدمة"),
        ("{t}: Common Pitfalls to Avoid", "{t}: أخطاء شائعة يجب تجنبها"),
        ("{t}: Patterns & Best Practices", "{t}: الأنماط وأفضل الممارسات"),
        ("{t}: Case Study", "{t}: دراسة حالة"),
        ("{t}: Mini Project", "{t}: مشروع مصغّر"),
    ],
    [
        ("{t}: Guided Walkthrough", "{t}: جولة موجّهة"),
        ("{t}: Building a Real Feature", "{t}: بناء ميزة حقيقية"),
        ("{t}: Debugging Session", "{t}: جلسة تصحيح أخطاء"),
        ("{t}: Performance Tips", "{t}: نصائح لتحسين الأداء"),
        ("{t}: Challenge Lab", "{t}: مختبر تحديات"),
    ],
    [
        ("{t}: Capstone Introduction", "{t}: مقدمة مشروع التخرج"),
        ("{t}: Planning Your Project", "{t}: تخطيط مشروعك"),
        ("{t}: Building the Project", "{t}: بناء المشروع"),
        ("{t}: Review & Feedback", "{t}: المراجعة والتغذية الراجعة"),
        ("{t}: Wrap-Up & What's Next", "{t}: الختام وما التالي"),
    ],
]

COMMENT_BODIES_EN = [
    "This lesson finally made it click for me. Thanks!",
    "Great explanation, clear and to the point.",
    "Could we get the slides as a downloadable resource?",
    "I love how practical this section is.",
    "The pacing is perfect for beginners.",
    "Watched it twice and learned something new both times.",
    "Small note: the shortcut at 04:12 saves so much time.",
    "This is exactly the kind of project-based teaching I was hoping for.",
]
COMMENT_BODIES_AR = [
    "شرح ممتاز، شكرًا لك!",
    "أخيرًا فهمت هذا المفهوم، الدورة رائعة.",
    "هل يمكن توفير ملفات الدرس للتحميل؟",
    "القسم عملي جدًا وأحببت ذلك.",
    "الوتيرة مثالية للمبتدئين.",
    "شاهدت الدرس مرتين وتعلمت شيئًا جديدًا في كل مرة.",
    "ملاحظة صغيرة: الاختصار في الدقيقة الرابعة يوفر وقتًا كبيرًا.",
    "هذا بالضبط نوع التعليم القائم على المشاريع الذي كنت أتمناه.",
]
REPLY_BODIES_EN = [
    "Same here, this helped a lot!",
    "Agreed, the explanation was crystal clear.",
    "Check the resources section, the files are there.",
    "Thanks for the tip, worked for me too.",
]
REPLY_BODIES_AR = [
    "وأنا كذلك، ساعدني هذا كثيرًا!",
    "أتفق معك، الشرح كان واضحًا تمامًا.",
    "تفضل بمراجعة قسم الموارد، الملفات موجودة هناك.",
    "شكرًا على المعلومة، نجحت معي أيضًا.",
]
REVIEW_EN = [
    "Excellent course, highly recommended.",
    "Clear explanations and great pacing.",
    "Exactly what I needed to get started.",
    "Good content, could use a few more exercises.",
    "Loved the hands-on project at the end.",
    "One of the best courses I have taken here.",
]
REVIEW_AR = [
    "دورة ممتازة، أنصح بها بشدة.",
    "شرح واضح وإيقاع رائع.",
    "بالضبط ما احتجته للبداية.",
    "محتوى جيد ويمكن إضافة تمارين أكثر.",
    "أحببت المشروع العملي في النهاية.",
    "من أفضل الدورات التي أخذتها هنا.",
]

# (language, title, excerpt, body) - blog posts are single-language by design.
BLOG_POSTS = [
    ("en", "Welcome to Coursaty: Learn Anything, Bilingually",
     "Why we built a bilingual learning platform, and what you can expect from it.",
     "Coursaty started with a simple question: why should great courses be locked behind a single language?\n\nEvery course on this platform is available in both English and Arabic, with a fully translated interface and right-to-left layout. Pick the language you think in, and switch any time. Our goal is simple: world-class content, in your language, at a fair price."),
    ("en", "How to Choose Your First Programming Language",
     "Python, JavaScript, or something else? A practical framework for deciding.",
     "The first language matters less than people think, but it still matters.\n\nChoose based on what you want to build: websites point to JavaScript, data and automation point to Python, mobile apps point to Swift or Kotlin. Whatever you pick, the real skill you are learning is how to think in code. Start building small projects in week one, and do not switch languages before finishing one."),
    ("en", "5 Habits of Highly Effective Self-Learners",
     "Small daily practices that compound into real skill over months.",
     "Consistency beats intensity, every single time.\n\nEffective self-learners schedule learning like a meeting, work in small daily sessions, build projects instead of only watching videos, track what they learn in a simple log, and teach what they know to someone else. None of these require talent. All of them require starting today."),
    ("en", "Getting Started with Web Development in 2026",
     "The modern stack, the right order to learn it, and what to ignore.",
     "The web platform keeps growing, but the fundamentals have been stable for years.\n\nStart with HTML and CSS, then JavaScript, then a framework like React or Django. Learn Git early. Deploy something, anything, to a real URL in your first month. Ignore the tooling debates until you have shipped a project; most of them will not matter for you yet."),
    ("en", "A Designer's Guide to Accessible Color",
     "Contrast ratios, color blindness, and palettes that work for everyone.",
     "Accessible color is not a constraint on good design; it is part of it.\n\nAim for a contrast ratio of at least 4.5:1 for body text, never use color as the only signal, and test your palette with a simulator for deuteranopia and protanopia. Building this habit early makes every future project better by default."),
    ("en", "The First 30 Days of Learning Something New",
     "A week-by-week plan for the fragile early phase of any new skill.",
     "The first month is where most learning projects die.\n\nWeek one: set a tiny daily minimum and protect the streak. Week two: finish one small tutorial end to end. Week three: build something tiny without a tutorial. Week four: share it publicly and ask for feedback. The goal of month one is not skill; it is proof that you can keep going."),
    ("ar", "مرحبًا بك في كورساتي: تعلّم أي شيء بلغتك",
     "لماذا بنينا منصة تعليمية ثنائية اللغة، وما الذي تتوقع منه.",
     "بدأت كورساتي من سؤال بسيط: لماذا تُحجز الدورات الممتازة خلف لغة واحدة؟\n\nكل دورة على هذه المنصة متاحة باللغتين العربية والإنجليزية، مع واجهة مترجمة بالكامل وتخطيط يدعم الاتجاه من اليمين إلى اليسار. اختر اللغة التي تفكر بها، وبدّل بينها متى شئت. هدفنا بسيط: محتوى عالمي، بلغتك، وبسعر عادل."),
    ("ar", "كيف تختار أول لغة برمجة تتعلمها؟",
     "بايثون أم جافاسكريبت أم غيرهما؟ إطار عملي لاتخاذ القرار.",
     "اللغة الأولى أقل أهمية مما يظن كثيرون، لكنها مع ذلك مهمة.\n\nاختر بناءً على ما تريد بناءه: مواقع الويب تشير إلى جافاسكريبت، والبيانات والأتمتة تشير إلى بايثون. أياً كانت لغتك الأولى، فالمهارة الحقيقية التي تكتسبها هي التفكير البرمجي. ابدأ بمشاريع صغيرة من الأسبوع الأول، ولا تبدّل لغتك قبل إنهاء مشروع كامل."),
    ("ar", "خمس عادات للمتعلمين الذاتيين الناجحين",
     "ممارسات يومية صغيرة تتراكم لتصنع مهارة حقيقية.",
     "الاستمرارية تتفوق على الحماس المكثف في كل مرة.\n\nالمتعلم الناجح يضع وقت التعلم في جدوله كأنه اجتماع، ويعمل بجلسات يومية قصيرة، ويبني مشاريع بدلًا من مشاهدة الفيديوهات فقط، ويسجل ما يتعلمه في سجل بسيط، ويعلّم ما يعرفه لشخص آخر. لا تتطلب هذه العادات موهبة، لكنها جميعًا تتطلب البدء اليوم."),
    ("ar", "الذكاء الاصطناعي: من أين تبدأ؟",
     "خارطة طريق عملية لدخول أحد أسرع المجالات نموًا.",
     "الذكاء الاصطناعي مجال واسع، لكن بدايته أوضح مما تتصور.\n\nابدأ بأساسيات بايثون وبعض الرياضيات، ثم تعلم أساسيات تعلم الآلة عمليًا، وبعدها اختر مسارًا: معالجة اللغات الطبيعية أو الرؤية الحاسوبية أو تحليل البيانات. القاعدة الذهبية: لا تشاهد فقط، بل طبّق كل مفهوم على مجموعة بيانات صغيرة."),
    ("ar", "دليل المبتدئين لتطوير الويب",
     "التقنيات الحديثة، والترتيب الصحيح لتعلمها، وما يجب تجاهله.",
     "منصة الويب تتوسع باستمرار، لكن أساسياتها مستقرة منذ سنوات.\n\nابدأ بلغتي HTML و CSS، ثم جافاسكريبت، ثم أطر عمل مثل React أو Django. تعلم Git مبكرًا، وانشر مشروعك على رابط حقيقي في أول شهر. تجاهل جدالات الأدوات حتى تنجز مشروعك الأول؛ فمعظمها لن يعنيك بعد."),
]

# (username, first_name, last_name, is_instructor)
DEMO_USERS = [
    ("sara.khalil", "Sara", "Khalil", True),
    ("karim.mostafa", "Karim", "Mostafa", True),
    ("lina.haddad", "Lina", "Haddad", True),
    ("omar.hassan", "Omar", "Hassan", False),
    ("nour.ahmed", "Nour", "Ahmed", False),
    ("dana.ali", "Dana", "Ali", False),
    ("youssef.kamal", "Youssef", "Kamal", False),
    ("mariam.salem", "Mariam", "Salem", False),
    ("tarek.zaki", "Tarek", "Zaki", False),
    ("salma.fahmy", "Salma", "Fahmy", False),
    ("ahmed.bakr", "Ahmed", "Bakr", False),
    ("layla.qasim", "Layla", "Qasim", False),
    ("khalid.mansour", "Khalid", "Mansour", False),
    ("rania.tawfik", "Rania", "Tawfik", False),
    ("hassan.kamal", "Hassan", "Kamal", False),
    ("sara.nasser", "Sara", "Nasser", False),
    ("mostafa.rady", "Mostafa", "Rady", False),
]

class Command(BaseCommand):
    help = ("Wipe the database and seed a full set of bilingual demo data. "
            "WARNING: flushes everything by default.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--images", required=True,
            help="Folder with thumbnail/cover images (jpg/png/webp).")
        parser.add_argument(
            "--admin-password",
            help="Password for the admin superuser; a random one is generated "
                 "and printed if omitted.")
        parser.add_argument(
            "--skip-wipe", action="store_true",
            help="Seed on top of existing data (debugging only).")
        parser.add_argument(
            "--cleanup-media", action="store_true",
            help="Delete old images under courses/thumbnails/ and courses/blog/ "
                 "on Cloudinary before seeding. Never touches videos.")

    # ------------------------------------------------------------------ setup

    def handle(self, *args, **options):
        images_dir = Path(options["images"])
        if not images_dir.is_dir():
            raise CommandError(f"Images folder not found: {images_dir}")
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        image_files = sorted(
            p for p in images_dir.iterdir() if p.suffix.lower() in exts)
        if not image_files:
            raise CommandError(f"No images found in {images_dir}")

        video_names = self._capture_video_names()
        if not video_names:
            raise CommandError(
                "No lesson videos found (neither in the database nor under "
                "courses/videos/ on Cloudinary).")

        if options["cleanup_media"]:
            self._cleanup_media()

        if not options["skip_wipe"]:
            self.stdout.write("Flushing the database ...")
            call_command("flush", interactive=False, verbosity=0)

        self._used_slugs = set()
        with translation.override("en"):
            result = self._seed(image_files, video_names)
        self._print_summary(result)

    def _capture_video_names(self):
        """Existing video references, so nothing is re-uploaded."""
        names = list(
            Lesson.objects.exclude(video="")
            .values_list("video", flat=True).distinct())
        if names:
            return names
        import cloudinary.api
        res = cloudinary.api.resources(
            resource_type="video", type="upload",
            prefix="courses/videos/", max_results=200)
        return [r["public_id"] for r in res.get("resources", [])]

    def _cleanup_media(self):
        import cloudinary.api
        for prefix in ("courses/thumbnails/", "courses/blog/"):
            self.stdout.write(f"Deleting old images under {prefix} ...")
            cloudinary.api.delete_resources_by_prefix(
                prefix, resource_type="image")

    # ------------------------------------------------------------------ seed

    def _seed(self, image_files, video_names):
        result = {}
        result["users"] = self._seed_users()
        self._instructor_cycle = itertools.cycle(result["users"]["instructors"])
        categories = self._seed_categories()
        videos_by_key = self._map_videos(video_names)
        result["courses"], result["lessons"] = self._seed_courses(
            image_files, videos_by_key, categories)
        result.update(self._seed_activity(result["users"], result["courses"]))
        result["posts"] = self._seed_blog(result["users"], image_files)
        return result

    def _seed_users(self):
        User = get_user_model()
        admin_password = secrets.token_urlsafe(12)
        admin = User.objects.create_superuser(
            username="admin", email="admin@example.com",
            password=admin_password)
        users = {
            "admin": admin,
            "admin_password": admin_password,
            "instructors": [],
            "students": [],
        }
        for username, first, last, is_instructor in DEMO_USERS:
            user = User.objects.create_user(
                username=username, email=f"{username}@example.com",
                password=DEMO_STUDENT_PASSWORD,
                first_name=first, last_name=last)
            key = "instructors" if is_instructor else "students"
            users[key].append(user)
        return users

    def _seed_categories(self):
        return {
            key: Category.objects.create(name_en=en, name_ar=ar)
            for key, en, ar in CATEGORIES
        }

    def _map_videos(self, video_names):
        """Assign each Cloudinary video to the categories it fits."""
        def keys_for(name):
            found = []
            if "جافاسكريبت" in name or "JavaScript" in name:
                found.append("web")
            if "PHP" in name or "Ruby" in name:
                found += ["web", "prog"]
            if "بايثون" in name or "ython" in name:
                found.append("prog")
            if "واجهات" in name:
                found.append("design")
            if "الذكاء" in name:
                found.append("ai")
            if "المنتجات" in name:
                found.append("business")
            if "الحاسوب" in name:
                found.append("cs")
            return found

        mapping = {key: [] for key, _, _ in CATEGORIES}
        for name in video_names:
            for key in keys_for(name) or list(mapping):
                mapping[key].append(name)
        for key, names in mapping.items():
            if not names:
                mapping[key] = list(video_names)
        return mapping

    def _unique_slug(self, text, max_length=50):
        slug = custom_slugify(text)[:max_length]
        base, n = slug, 2
        while slug in self._used_slugs:
            suffix = f"-{n}"
            slug = f"{base[:max_length - len(suffix)]}{suffix}"
            n += 1
        self._used_slugs.add(slug)
        return slug

    def _seed_courses(self, image_files, videos_by_key, categories):
        deepmind = [p for p in image_files if "deepmind" in p.name.lower()]
        general = [p for p in image_files if "deepmind" not in p.name.lower()]
        ai_count = len(COURSES["ai"])
        ai_pool = deepmind + general[:max(0, ai_count - len(deepmind))]
        rest = general[max(0, ai_count - len(deepmind)):]
        rest_cycle = itertools.cycle(rest)

        image_plan = {}
        for i in range(ai_count):
            image_plan[("ai", i)] = ai_pool[i % len(ai_pool)]
        for key, titles in COURSES.items():
            if key == "ai":
                continue
            for i in range(len(titles)):
                image_plan[(key, i)] = next(rest_cycle)

        instructors = None  # filled on first use from users
        total = sum(len(v) for v in COURSES.values())
        counter = 0
        courses = []
        lesson_count = 0
        for key, titles in COURSES.items():
            category = categories[key]
            cat_en = dict((k, e) for k, e, _ in CATEGORIES)[key]
            cat_ar = dict((k, a) for k, _, a in CATEGORIES)[key]
            videos = videos_by_key[key]
            for idx, (title_en, title_ar) in enumerate(titles):
                counter += 1
                # leave the last course of three categories unpublished
                is_published = not (key in ("web", "ai", "cs")
                                    and idx == len(titles) - 1)
                image_path = image_plan[(key, idx)]
                with open(image_path, "rb") as fh:
                    course = Course.objects.create(
                        category=category,
                        created_by=self._next_instructor(),
                        title_en=title_en,
                        title_ar=title_ar,
                        short_description_en=random.choice(SHORT_DESC_EN).format(t=title_en),
                        short_description_ar=random.choice(SHORT_DESC_AR).format(t=title_ar),
                        description_en=random.choice(DESC_EN).format(t=title_en, c=cat_en),
                        description_ar=random.choice(DESC_AR).format(t=title_ar, c=cat_ar),
                        what_you_learn_en=random.choice(WHAT_YOU_LEARN_EN).format(t=title_en),
                        what_you_learn_ar=random.choice(WHAT_YOU_LEARN_AR).format(t=title_ar),
                        requirements_en=random.choice(REQUIREMENTS_EN).format(c=cat_en),
                        requirements_ar=random.choice(REQUIREMENTS_AR).format(c=cat_ar),
                        price=random.choice(PRICES),
                        is_published=is_published,
                        thumbnail=File(fh, name=image_path.name),
                    )
                created = timezone.now() - timedelta(days=random.randint(5, 300))
                Course.objects.filter(pk=course.pk).update(
                    created_at=created,
                    last_updated=created + timedelta(days=random.randint(0, 30)))
                courses.append(course)

                sections_en, sections_ar = random.choice(SECTION_ARCHETYPES)
                sections = Section.objects.bulk_create([
                    Section(course=course, title_en=sections_en[i],
                            title_ar=sections_ar[i], order=i + 1)
                    for i in range(len(sections_en))
                ])
                lessons = []
                for s_idx, section in enumerate(sections):
                    for l_idx, (t_en, t_ar) in enumerate(LESSON_TEMPLATES[s_idx]):
                        lessons.append(Lesson(
                            section=section,
                            title_en=t_en.format(t=title_en),
                            title_ar=t_ar.format(t=title_ar),
                            video=videos[(counter + s_idx * 5 + l_idx) % len(videos)],
                            duration=timedelta(minutes=random.randint(4, 20)),
                            order=l_idx + 1,
                            slug=self._unique_slug(t_en.format(t=title_en)),
                        ))
                Lesson.objects.bulk_create(lessons, batch_size=100)
                lesson_count += len(lessons)

                if counter % 10 == 0 or counter == total:
                    self.stdout.write(f"  seeded {counter}/{total} courses ...")
        return courses, lesson_count

    def _next_instructor(self):
        return next(self._instructor_cycle)

    def _seed_activity(self, users, courses):
        students = users["students"]
        published = [c for c in courses if c.is_published]

        enrollments = []
        enrolled_by_course = {}
        for course in published:
            chosen = random.sample(students, random.randint(1, 4))
            enrolled_by_course[course.pk] = chosen
            enrollments += [
                Enrollment(user=u, course=course) for u in chosen]
        Enrollment.objects.bulk_create(enrollments)

        payments = []
        n = 0
        for e in enrollments:
            if random.random() < 0.75:
                n += 1
                payments.append(Payment(
                    user=e.user, course=e.course,
                    stripe_session_id=f"cs_demo_{n:05d}",
                    amount=e.course.price, status="completed"))
        for status in ("pending", "pending", "failed", "failed", "failed"):
            n += 1
            course = random.choice(published)
            payments.append(Payment(
                user=random.choice(students), course=course,
                stripe_session_id=f"cs_demo_{n:05d}",
                amount=course.price, status=status))
        Payment.objects.bulk_create(payments)

        ratings = []
        for course in published:
            enrolled = enrolled_by_course.get(course.pk, [])
            for u in random.sample(enrolled, min(random.randint(2, 6), len(enrolled))):
                review = ""
                if random.random() < 0.55:
                    pool = REVIEW_EN if random.random() < 0.6 else REVIEW_AR
                    review = random.choice(pool)
                ratings.append(Rating(
                    user=u, course=course,
                    score=random.choice([5, 5, 5, 5, 4, 4, 4, 3, 3, 2]),
                    review=review))
        Rating.objects.bulk_create(ratings)

        lessons_by_course = defaultdict(list)
        for row in Lesson.objects.values_list("id", "section__course_id"):
            lessons_by_course[row[1]].append(row[0])

        pairs = random.sample(enrollments, min(35, len(enrollments)))
        parents, parent_course_ids = [], []
        for e in pairs:
            lesson_ids = lessons_by_course.get(e.course_id) or []
            if not lesson_ids:
                continue
            pool = (COMMENT_BODIES_EN if random.random() < 0.6
                    else COMMENT_BODIES_AR)
            parents.append(Comment(
                user=e.user, lesson_id=random.choice(lesson_ids),
                body=random.choice(pool)))
            parent_course_ids.append(e.course_id)
        Comment.objects.bulk_create(parents)

        replies = []
        for comment, course_id in zip(parents, parent_course_ids):
            if random.random() < 0.5:
                others = [u for u in enrolled_by_course.get(course_id, [])
                          if u != comment.user]
                if others:
                    pool = (REPLY_BODIES_EN if random.random() < 0.6
                            else REPLY_BODIES_AR)
                    replies.append(Comment(
                        user=random.choice(others),
                        lesson_id=comment.lesson_id,
                        body=random.choice(pool), parent=comment))
        Comment.objects.bulk_create(replies)

        wishlist = []
        for u in students:
            enrolled_pks = {e.course_id for e in enrollments
                            if e.user_id == u.pk}
            options = [c for c in published if c.pk not in enrolled_pks]
            for c in random.sample(options, min(random.randint(0, 3), len(options))):
                wishlist.append(Wishlist(user=u, course=c))
        Wishlist.objects.bulk_create(wishlist)

        return {
            "enrollments": len(enrollments),
            "payments": len(payments),
            "ratings": len(ratings),
            "comments": len(parents) + len(replies),
            "wishlist": len(wishlist),
        }

    def _seed_blog(self, users, image_files):
        authors = [users["admin"]] + users["instructors"]
        covers = itertools.cycle(image_files)
        posts = []
        for i, (_lang, title, excerpt, body) in enumerate(BLOG_POSTS):
            cover = next(covers)
            post = Post(
                author=authors[i % len(authors)],
                title=title, excerpt=excerpt, body=body)
            with open(cover, "rb") as fh:
                post.cover_image = File(fh, name=cover.name)
                post.save()
            created = timezone.now() - timedelta(days=random.randint(1, 150))
            Post.objects.filter(pk=post.pk).update(
                created_at=created,
                updated_at=created + timedelta(days=random.randint(0, 10)))
            posts.append(post)
        return posts

    # ------------------------------------------------------------------ output

    def _print_summary(self, result):
        users = result["users"]
        published = sum(1 for c in result["courses"] if c.is_published)
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully:"))
        self.stdout.write(f"  users:        18 (1 admin, 3 instructors, 14 students)")
        self.stdout.write(f"  categories:   {Category.objects.count()}")
        self.stdout.write(f"  courses:      {Course.objects.count()} "
                          f"({published} published)")
        self.stdout.write(f"  lessons:      {Lesson.objects.count()}")
        self.stdout.write(f"  enrollments:  {result['enrollments']}")
        self.stdout.write(f"  payments:     {result['payments']}")
        self.stdout.write(f"  ratings:      {result['ratings']}")
        self.stdout.write(f"  comments:     {result['comments']}")
        self.stdout.write(f"  wishlist:     {result['wishlist']}")
        self.stdout.write(f"  blog posts:   {len(result['posts'])}")
        self.stdout.write("")
        self.stdout.write("Logins:")
        self.stdout.write(f"  admin / {users['admin_password']}  (admin panel)")
        self.stdout.write(f"  demo users / {DEMO_STUDENT_PASSWORD}")
        self.stdout.write("  e.g. omar.hassan, sara.khalil, dana.ali")
