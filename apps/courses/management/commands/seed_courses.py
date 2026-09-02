"""
Management command to seed courses and lessons for Cybersecurity and AI & Machine Learning career paths.
"""
from django.core.management.base import BaseCommand
from apps.careers.models import Career
from apps.courses.models import Course, Lesson


CYBERSECURITY_COURSES = [
    {
        'title': 'Network Security Fundamentals',
        'description': 'Master the core concepts of network security including firewalls, VPNs, intrusion detection, and secure network architecture. This course provides hands-on experience with industry-standard tools and frameworks.',
        'module_number': 1,
        'duration_minutes': 180,
        'order': 1,
        'lessons': [
            {
                'title': 'Introduction to Network Security',
                'content_html': (
                    '<p>Network security is the practice of protecting computer networks from unauthorized access, '
                    'misuse, modification, or denial of service. In today\'s interconnected world, every organization '
                    'relies on networks to conduct business, making network security a critical discipline.</p>'
                    '<p>This lesson covers the fundamental principles: confidentiality, integrity, and availability '
                    '(the CIA triad). You\'ll learn about common network architectures, the OSI model, and how '
                    'security controls map to each layer.</p>'
                    '<p>By the end of this lesson, you will understand the threat landscape facing modern networks '
                    'and be able to identify the key components of a defense-in-depth strategy.</p>'
                ),
                'order': 1,
                'duration_minutes': 45,
                'quiz_question': 'Which layer of the OSI model is primarily responsible for routing and logical addressing?',
                'quiz_options': ['Physical Layer', 'Data Link Layer', 'Network Layer', 'Transport Layer'],
                'quiz_correct_index': 2,
                'quiz_feedback': 'The Network Layer (Layer 3) handles routing, logical addressing (IP addresses), and path determination. Routers operate at this layer.',
            },
            {
                'title': 'Firewalls and Network Segmentation',
                'content_html': (
                    '<p>Firewalls are the first line of defense in network security. They monitor and control '
                    'incoming and outgoing network traffic based on predetermined security rules. Modern firewalls '
                    'have evolved from simple packet filters to next-generation firewalls with deep packet inspection, '
                    'application awareness, and integrated threat intelligence.</p>'
                    '<p>Network segmentation divides a network into smaller, isolated segments, limiting the lateral '
                    'movement of attackers. We\'ll explore DMZs, VLANs, zero-trust segmentation, and micro-segmentation '
                    'strategies used in cloud environments.</p>'
                ),
                'order': 2,
                'duration_minutes': 50,
                'quiz_question': 'What is the primary purpose of a DMZ (Demilitarized Zone) in network architecture?',
                'quiz_options': [
                    'To store sensitive database servers',
                    'To host public-facing services while isolating them from the internal network',
                    'To connect branch offices securely',
                    'To provide wireless access for guests'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'A DMZ is a perimeter network that hosts public-facing services (web servers, email servers) while keeping them isolated from the internal trusted network. If compromised, the attacker cannot directly access internal systems.',
            },
            {
                'title': 'Intrusion Detection and Prevention Systems',
                'content_html': (
                    '<p>Intrusion Detection Systems (IDS) and Intrusion Prevention Systems (IPS) are critical '
                    'components of network defense. While firewalls enforce policy at the perimeter, IDS/IPS '
                    'monitor for suspicious activity within the network.</p>'
                    '<p>This lesson distinguishes between signature-based detection (matching known attack patterns) '
                    'and anomaly-based detection (identifying deviations from normal behavior). We\'ll examine '
                    'popular tools like Snort, Suricata, and Zeek, and discuss deployment strategies: network-based '
                    '(NIDS/NIPS) versus host-based (HIDS/HIPS).</p>'
                ),
                'order': 3,
                'duration_minutes': 45,
            },
            {
                'title': 'VPNs and Secure Remote Access',
                'content_html': (
                    '<p>Virtual Private Networks (VPNs) create encrypted tunnels over public networks, enabling '
                    'secure remote access to corporate resources. With the rise of remote work, VPNs have become '
                    'essential infrastructure.</p>'
                    '<p>We cover IPsec VPNs, SSL/TLS VPNs, and modern alternatives like WireGuard and zero-trust '
                    'network access (ZTNA). You\'ll learn about authentication methods, split tunneling vs. full '
                    'tunneling, and how to configure and troubleshoot common VPN issues.</p>'
                ),
                'order': 4,
                'duration_minutes': 40,
                'quiz_question': 'What is the key difference between split tunneling and full tunneling in a VPN configuration?',
                'quiz_options': [
                    'Split tunneling encrypts only HTTP traffic; full tunneling encrypts all traffic',
                    'Split tunneling routes only corporate traffic through the VPN; full tunneling routes all traffic through the VPN',
                    'Split tunneling uses IPsec; full tunneling uses SSL/TLS',
                    'Split tunneling is faster but less secure; full tunneling is slower but more secure'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'Split tunneling routes only traffic destined for corporate networks through the VPN tunnel, while other traffic (like internet browsing) goes directly. Full tunneling routes all traffic through the VPN, providing more security but higher latency and bandwidth usage.',
            },
        ],
    },
    {
        'title': 'Ethical Hacking and Penetration Testing',
        'description': 'Learn the methodologies and tools used by ethical hackers to identify and exploit vulnerabilities in systems and networks. This course follows the penetration testing execution standard (PTES) and prepares you for certifications like CEH and OSCP.',
        'module_number': 2,
        'duration_minutes': 240,
        'order': 2,
        'lessons': [
            {
                'title': 'Penetration Testing Methodology',
                'content_html': (
                    '<p>Penetration testing is a structured process, not a random attempt at breaking in. '
                    'Professional pen testers follow established methodologies such as PTES (Penetration Testing '
                    'Execution Standard), NIST SP 800-115, and the OWASP Testing Guide.</p>'
                    '<p>This lesson walks through the seven phases: Pre-engagement, Intelligence Gathering, '
                    'Threat Modeling, Vulnerability Analysis, Exploitation, Post-Exploitation, and Reporting. '
                    'You\'ll learn the importance of rules of engagement, scope definition, and maintaining '
                    'professional ethics throughout the engagement.</p>'
                ),
                'order': 1,
                'duration_minutes': 50,
                'quiz_question': 'Which phase of the PTES methodology involves defining the scope, rules of engagement, and legal agreements?',
                'quiz_options': [
                    'Intelligence Gathering',
                    'Pre-engagement',
                    'Threat Modeling',
                    'Vulnerability Analysis'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'Pre-engagement is the initial phase where scope, objectives, rules of engagement, legal agreements, and communication plans are established before any testing begins.',
            },
            {
                'title': 'Reconnaissance and Information Gathering',
                'content_html': (
                    '<p>Reconnaissance is the foundation of a successful penetration test. The more information '
                    'you gather about a target, the more effective your attack vectors will be. This phase is '
                    'divided into passive reconnaissance (gathering info without directly interacting with the '
                    'target) and active reconnaissance (directly probing the target).</p>'
                    '<p>We cover OSINT techniques: WHOIS lookups, DNS enumeration, certificate transparency logs, '
                    'social media intelligence, Google dorks, and tools like Maltego, theHarvester, and Recon-ng. '
                    'You\'ll also learn active techniques: port scanning with Nmap, service enumeration, and '
                    'banner grabbing.</p>'
                ),
                'order': 2,
                'duration_minutes': 60,
            },
            {
                'title': 'Vulnerability Scanning and Analysis',
                'content_html': (
                    '<p>After reconnaissance, the next step is identifying vulnerabilities in the target systems. '
                    'Vulnerability scanning automates the discovery of known security flaws using databases like '
                    'CVE (Common Vulnerabilities and Exposures) and NVD (National Vulnerability Database).</p>'
                    '<p>This lesson covers Nessus, OpenVAS, and Nuclei for automated scanning. You\'ll learn how '
                    'to interpret scan results, prioritize findings using CVSS (Common Vulnerability Scoring System), '
                    'and distinguish between false positives and genuine exploitable vulnerabilities. We also '
                    'discuss credentialed vs. non-credentialed scans and compliance scanning.</p>'
                ),
                'order': 3,
                'duration_minutes': 55,
                'quiz_question': 'What does a CVSS base score of 9.8 indicate about a vulnerability?',
                'quiz_options': [
                    'Low severity - minimal impact',
                    'Medium severity - moderate impact',
                    'High severity - significant impact',
                    'Critical severity - severe impact'
                ],
                'quiz_correct_index': 3,
                'quiz_feedback': 'CVSS scores range from 0.0 to 10.0. A score of 9.0-10.0 is rated Critical, indicating a vulnerability that is easily exploitable, requires no user interaction, and has severe impact on confidentiality, integrity, and availability.',
            },
            {
                'title': 'Exploitation and Post-Exploitation',
                'content_html': (
                    '<p>Exploitation is the act of leveraging a vulnerability to gain unauthorized access or '
                    'escalate privileges. This lesson emphasizes controlled, authorized exploitation within the '
                    'defined scope of a penetration test.</p>'
                    '<p>We introduce the Metasploit Framework, manual exploitation techniques, and privilege '
                    'escalation on Windows and Linux. Post-exploitation covers maintaining access, pivoting to '
                    'other systems, credential harvesting, and data exfiltration simulation. The goal is to '
                    'demonstrate business impact, not to cause damage.</p>'
                ),
                'order': 4,
                'duration_minutes': 75,
            },
        ],
    },
    {
        'title': 'Security Operations and Incident Response',
        'description': 'Build the skills needed to detect, analyze, and respond to security incidents in a professional SOC environment. Learn SIEM usage, log analysis, threat hunting, and the incident response lifecycle.',
        'module_number': 3,
        'duration_minutes': 210,
        'order': 3,
        'lessons': [
            {
                'title': 'SOC Fundamentals and SIEM',
                'content_html': (
                    '<p>A Security Operations Center (SOC) is the nerve center of an organization\'s cyber '
                    'defense. SOC analysts monitor, detect, investigate, and respond to security events 24/7.</p>'
                    '<p>This lesson introduces the SOC tier structure (Tier 1: Monitoring, Tier 2: Analysis, '
                    'Tier 3: Threat Hunting/IR), key performance metrics (MTTD, MTTR), and the role of SIEM '
                    '(Security Information and Event Management) platforms like Splunk, Elastic, and Microsoft '
                    'Sentinel. You\'ll learn about log sources, normalization, correlation rules, and alert tuning.</p>'
                ),
                'order': 1,
                'duration_minutes': 50,
                'quiz_question': 'What is the primary difference between Tier 1 and Tier 2 SOC analysts?',
                'quiz_options': [
                    'Tier 1 handles incident response; Tier 2 handles monitoring',
                    'Tier 1 performs initial triage and escalation; Tier 2 performs deep investigation and analysis',
                    'Tier 1 manages SIEM rules; Tier 2 manages firewalls',
                    'Tier 1 works day shifts; Tier 2 works night shifts'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'Tier 1 analysts monitor alerts, perform initial triage, and escalate genuine incidents. Tier 2 analysts conduct deeper investigation, malware analysis, and threat hunting.',
            },
            {
                'title': 'Incident Response Lifecycle',
                'content_html': (
                    '<p>Incident response is a structured approach to handling security breaches. The NIST SP 800-61 '
                    'framework defines four phases: Preparation, Detection & Analysis, Containment, Eradication & '
                    'Recovery, and Post-Incident Activity.</p>'
                    '<p>This lesson walks through each phase with practical examples. You\'ll learn to create '
                    'incident response playbooks, establish communication plans, preserve forensic evidence, '
                    'and conduct root cause analysis. Tabletop exercises and red team/blue team simulations are '
                    'covered as preparation techniques.</p>'
                ),
                'order': 2,
                'duration_minutes': 60,
            },
            {
                'title': 'Threat Hunting and Threat Intelligence',
                'content_html': (
                    '<p>Threat hunting is proactive: instead of waiting for alerts, hunters actively search for '
                    'adversaries who have evaded existing defenses. This requires deep knowledge of adversary '
                    'tactics, techniques, and procedures (TTPs) as documented in the MITRE ATT&CK framework.</p>'
                    '<p>We cover hypothesis-driven hunting, intelligence-driven hunting, and situational awareness. '
                    'You\'ll learn to consume threat intelligence feeds (STIX/TAXII, MISP), create hunt hypotheses, '
                    'and use tools like Velociraptor, Osquery, and Sigma rules for endpoint and network hunting.</p>'
                    '<p>By the end, you\'ll be able to design and execute a threat hunt from hypothesis to findings.</p>'
                ),
                'order': 3,
                'duration_minutes': 50,
                'quiz_question': 'In the MITRE ATT&CK framework, what does the "Initial Access" tactic represent?',
                'quiz_options': [
                    'Techniques used to maintain persistence on a compromised system',
                    'Techniques used to gain an initial foothold in a target environment',
                    'Techniques used to escalate privileges after initial access',
                    'Techniques used to move laterally across the network'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'Initial Access (TA0001) covers techniques that allow an adversary to gain an initial foothold in a target environment, such as phishing, drive-by compromise, exploitation of public-facing applications, and valid accounts.',
            },
            {
                'title': 'Malware Analysis Basics',
                'content_html': (
                    '<p>Malware analysis is the process of understanding the behavior, purpose, and impact of '
                    'malicious software. This lesson introduces both static analysis (examining code without '
                    'executing it) and dynamic analysis (observing behavior in a controlled environment).</p>'
                    '<p>You\'ll learn to set up a safe analysis lab (VMs, snapshots, network simulation), use '
                    'tools like PEiD, strings, YARA, Cuckoo Sandbox, and CAPA. We cover common malware types '
                    '(ransomware, trojans, RATs, droppers), obfuscation techniques (packing, encryption, '
                    'anti-analysis), and how to extract IOCs (Indicators of Compromise) for detection.</p>'
                ),
                'order': 4,
                'duration_minutes': 50,
            },
        ],
    },
]


AI_ML_COURSES = [
    {
        'title': 'Python for Machine Learning',
        'description': 'Build a rock-solid foundation in Python programming tailored for machine learning. Covers NumPy, Pandas, Matplotlib, Scikit-learn, and best practices for reproducible ML workflows.',
        'module_number': 1,
        'duration_minutes': 180,
        'order': 1,
        'lessons': [
            {
                'title': 'NumPy Fundamentals for ML',
                'content_html': (
                    '<p>NumPy is the foundation of the Python scientific computing stack. Every major ML library—'
                    'Pandas, Scikit-learn, TensorFlow, PyTorch—builds on NumPy arrays. Understanding NumPy '
                    'deeply will make you more effective at data manipulation, debugging, and writing performant code.</p>'
                    '<p>This lesson covers ndarray creation, indexing, slicing, broadcasting, vectorization, and '
                    'common operations: reshaping, stacking, splitting, and mathematical functions. You\'ll learn '
                    'why vectorized operations are orders of magnitude faster than Python loops and how to leverage '
                    'broadcasting rules for clean, efficient code.</p>'
                ),
                'order': 1,
                'duration_minutes': 45,
                'quiz_question': 'What is the result of broadcasting a (3, 4) array with a (4,) array in NumPy?',
                'quiz_options': [
                    'Error: shapes are incompatible',
                    'A (3, 4) array where the (4,) array is added to each row',
                    'A (4, 3) array where the (4,) array is added to each column',
                    'A (3, 4) array where the (4,) array is added to each column'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'NumPy broadcasting aligns shapes from right to left. A (3, 4) array and a (4,) array are compatible: the (4,) array is treated as (1, 4) and broadcast across the first dimension, adding to each row.',
            },
            {
                'title': 'Data Manipulation with Pandas',
                'content_html': (
                    '<p>Pandas is the go-to library for structured data manipulation in Python. Its two primary '
                    'data structures—Series (1D) and DataFrame (2D)—provide powerful tools for cleaning, '
                    'transforming, and analyzing tabular data.</p>'
                    '<p>This lesson covers DataFrame creation, reading/writing CSV, Parquet, and Excel files, '
                    'indexing with .loc and .iloc, filtering, grouping and aggregation (groupby), pivot tables, '
                    'handling missing data, merging/joining DataFrames, and time series operations. You\'ll also '
                    'learn performance tips: avoiding chained indexing, using vectorized string operations, and '
                    'leveraging categorical dtypes for memory efficiency.</p>'
                ),
                'order': 2,
                'duration_minutes': 50,
            },
            {
                'title': 'Data Visualization for Exploratory Analysis',
                'content_html': (
                    '<p>Visualization is essential for understanding data distributions, relationships, and '
                    'anomalies before modeling. While Matplotlib provides the foundation, Seaborn and Plotly '
                    'offer higher-level interfaces for statistical visualizations.</p>'
                    '<p>This lesson covers histograms, box plots, violin plots, scatter plots, pair plots, '
                    'correlation heatmaps, and distribution plots. You\'ll learn to customize aesthetics, '
                    'create publication-quality figures, and build interactive visualizations with Plotly for '
                    'exploratory data analysis (EDA) workflows.</p>'
                ),
                'order': 3,
                'duration_minutes': 40,
                'quiz_question': 'Which visualization is most appropriate for showing the distribution of a single continuous variable?',
                'quiz_options': [
                    'Scatter plot',
                    'Box plot',
                    'Bar chart',
                    'Pie chart'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'A box plot (or histogram/violin plot) shows the distribution of a continuous variable including median, quartiles, and outliers. Scatter plots show relationships between two variables; bar and pie charts are for categorical data.',
            },
            {
                'title': 'Introduction to Scikit-learn',
                'content_html': (
                    '<p>Scikit-learn is the most widely used ML library in Python for classical machine learning '
                    'algorithms. Its consistent estimator API (fit, predict, transform) makes it easy to experiment '
                    'with different models and build pipelines.</p>'
                    '<p>This lesson introduces the core concepts: estimators, transformers, predictors, pipelines, '
                    'cross-validation, and model evaluation metrics. We cover preprocessing (StandardScaler, '
                    'OneHotEncoder, ColumnTransformer), linear models, tree-based models, and model selection '
                    'with GridSearchCV and RandomizedSearchCV.</p>'
                ),
                'order': 4,
                'duration_minutes': 45,
                'quiz_question': 'What is the purpose of a Pipeline in scikit-learn?',
                'quiz_options': [
                    'To chain multiple estimators together so they can be cross-validated as a single unit',
                    'To automatically select the best hyperparameters for a model',
                    'To visualize the decision boundaries of a classifier',
                    'To parallelize model training across multiple CPU cores'
                ],
                'quiz_correct_index': 0,
                'quiz_feedback': 'A Pipeline chains transformers and an estimator into a single object. This prevents data leakage during cross-validation (preprocessing is fit only on training folds) and simplifies model deployment.',
            },
        ],
    },
    {
        'title': 'Supervised Learning Algorithms',
        'description': 'Deep dive into the core supervised learning algorithms: linear regression, logistic regression, decision trees, random forests, gradient boosting, and support vector machines. Learn when to use each and how to tune them effectively.',
        'module_number': 2,
        'duration_minutes': 240,
        'order': 2,
        'lessons': [
            {
                'title': 'Linear and Logistic Regression',
                'content_html': (
                    '<p>Linear regression and logistic regression are the starting points for understanding '
                    'supervised learning. Despite their simplicity, they remain widely used in industry for '
                    'their interpretability and strong baseline performance.</p>'
                    '<p>This lesson covers the mathematical formulation, assumptions (linearity, independence, '
                    'homoscedasticity, normality), regularization (Ridge, Lasso, Elastic Net), and interpretation '
                    'of coefficients. For logistic regression, we cover the sigmoid function, log-odds, '
                    'decision boundaries, and probability calibration. You\'ll learn to diagnose multicollinearity '
                    'with VIF and assess model fit with residual plots.</p>'
                ),
                'order': 1,
                'duration_minutes': 55,
                'quiz_question': 'What does L1 regularization (Lasso) do that L2 regularization (Ridge) does not?',
                'quiz_options': [
                    'Prevents overfitting more effectively',
                    'Can drive coefficients exactly to zero, performing feature selection',
                    'Works better with correlated features',
                    'Produces more stable coefficient estimates'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'L1 regularization adds a penalty proportional to the absolute value of coefficients, which can shrink some coefficients exactly to zero, effectively performing feature selection. L2 (Ridge) shrinks coefficients toward zero but rarely eliminates them entirely.',
            },
            {
                'title': 'Decision Trees and Ensemble Methods',
                'content_html': (
                    '<p>Decision trees are intuitive, interpretable models that partition the feature space into '
                    'rectangular regions. While a single tree tends to overfit, ensemble methods combine multiple '
                    'trees to achieve state-of-the-art performance on tabular data.</p>'
                    '<p>This lesson covers tree construction (Gini impurity, entropy, information gain), pruning, '
                    'and the bias-variance tradeoff. We then explore Random Forests (bagging), Gradient Boosting '
                    '(XGBoost, LightGBM, CatBoost), and stacking. You\'ll learn key hyperparameters: n_estimators, '
                    'max_depth, learning_rate, subsample, and how to handle categorical features natively in modern '
                    'boosting libraries.</p>'
                ),
                'order': 2,
                'duration_minutes': 65,
            },
            {
                'title': 'Support Vector Machines and Kernel Methods',
                'content_html': (
                    '<p>Support Vector Machines (SVMs) find the optimal hyperplane that maximizes the margin '
                    'between classes. With kernel tricks, SVMs can model complex non-linear decision boundaries '
                    'without explicitly transforming features into high-dimensional space.</p>'
                    '<p>This lesson covers the optimization problem (hinge loss, regularization parameter C), '
                    'kernel functions (linear, polynomial, RBF, sigmoid), and the dual formulation. You\'ll learn '
                    'when SVMs excel (small to medium datasets, high-dimensional spaces) and their limitations '
                    '(scalability, sensitivity to outliers, probability calibration challenges).</p>'
                ),
                'order': 3,
                'duration_minutes': 50,
                'quiz_question': 'What is the primary role of the C parameter in a Support Vector Machine?',
                'quiz_options': [
                    'Controls the kernel function type',
                    'Controls the trade-off between maximizing the margin and minimizing classification error',
                    'Determines the number of support vectors',
                    'Sets the maximum number of iterations for the solver'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'C is the regularization parameter. A small C creates a wider margin but allows more misclassifications (underfitting). A large C creates a narrower margin with fewer training errors (risk of overfitting).',
            },
            {
                'title': 'Model Evaluation and Validation',
                'content_html': (
                    '<p>Building a model is only half the battle; evaluating it correctly is equally critical. '
                    'This lesson covers the full evaluation toolkit for classification and regression tasks.</p>'
                    '<p>For classification: accuracy, precision, recall, F1-score, ROC-AUC, PR-AUC, confusion '
                    'matrices, and calibration curves. For regression: MAE, MSE, RMSE, R², MAPE. We cover '
                    'cross-validation strategies (k-fold, stratified, grouped, time series split), nested CV for '
                    'unbiased performance estimates, and statistical significance testing. You\'ll also learn '
                    'about data leakage—one of the most common pitfalls in ML—and how to prevent it.</p>'
                ),
                'order': 4,
                'duration_minutes': 70,
                'quiz_question': 'When evaluating a binary classifier on an imbalanced dataset (99% negative, 1% positive), why is accuracy a misleading metric?',
                'quiz_options': [
                    'Accuracy is computationally expensive to compute',
                    'A model that always predicts the majority class achieves 99% accuracy but is useless',
                    'Accuracy requires probability estimates which are not always available',
                    'Accuracy only works for multi-class problems'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'On a 99/1 imbalanced dataset, a dummy classifier predicting "negative" for everything achieves 99% accuracy but has 0% recall for the positive class. Precision, recall, F1, and ROC-AUC are more informative for imbalanced problems.',
            },
        ],
    },
    {
        'title': 'Neural Networks and Deep Learning',
        'description': 'Transition from classical ML to deep learning. Understand neural network architecture, backpropagation, and build models with PyTorch. Covers MLPs, CNNs, RNNs, and modern architectures.',
        'module_number': 3,
        'duration_minutes': 300,
        'order': 3,
        'lessons': [
            {
                'title': 'Neural Network Fundamentals',
                'content_html': (
                    '<p>Neural networks are universal function approximators inspired by biological neurons. '
                    'A neural network consists of layers of interconnected nodes (neurons) that transform '
                    'input data through weighted sums and non-linear activation functions.</p>'
                    '<p>This lesson covers the perceptron, multi-layer perceptrons (MLPs), activation functions '
                    '(ReLU, sigmoid, tanh, GELU, Swish), loss functions (MSE, cross-entropy), and the '
                    'backpropagation algorithm for computing gradients. You\'ll implement a simple neural network '
                    'from scratch using only NumPy to understand the mechanics before moving to PyTorch.</p>'
                ),
                'order': 1,
                'duration_minutes': 60,
                'quiz_question': 'Why is the ReLU activation function (max(0, x)) preferred over sigmoid in deep networks?',
                'quiz_options': [
                    'ReLU is differentiable everywhere',
                    'ReLU does not suffer from the vanishing gradient problem for positive inputs',
                    'ReLU produces outputs in the range [0, 1]',
                    'ReLU is computationally more expensive but more accurate'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'ReLU\'s gradient is 1 for positive inputs, allowing gradients to flow unchanged through many layers. Sigmoid\'s gradient is at most 0.25, causing gradients to vanish exponentially in deep networks. ReLU is also faster to compute.',
            },
            {
                'title': 'Introduction to PyTorch',
                'content_html': (
                    '<p>PyTorch is a dynamic deep learning framework that has become the research standard and '
                    'is widely used in production. Its dynamic computation graph (define-by-run) makes debugging '
                    'intuitive and Pythonic.</p>'
                    '<p>This lesson covers tensors, autograd (automatic differentiation), nn.Module for building '
                    'models, DataLoader for batching, optimizers (SGD, Adam, AdamW), and learning rate schedulers. '
                    'You\'ll build and train your first MLP on a classification task, visualize training curves, '
                    'and learn to save/load model checkpoints.</p>'
                ),
                'order': 2,
                'duration_minutes': 60,
            },
            {
                'title': 'Convolutional Neural Networks (CNNs)',
                'content_html': (
                    '<p>CNNs revolutionized computer vision by exploiting spatial locality and translation '
                    'invariance through convolution operations. They are the backbone of modern vision systems.</p>'
                    '<p>This lesson covers convolution, pooling, padding, stride, receptive fields, and classic '
                    'architectures: LeNet, AlexNet, VGG, ResNet, EfficientNet. You\'ll learn about residual '
                    'connections, batch normalization, data augmentation, transfer learning with pretrained models, '
                    'and how to adapt a pretrained ResNet for a custom classification task using PyTorch.</p>'
                ),
                'order': 3,
                'duration_minutes': 70,
                'quiz_question': 'What is the key innovation of ResNet that enables training very deep networks?',
                'quiz_options': [
                    'Using 1x1 convolutions to reduce parameters',
                    'Residual connections (skip connections) that allow gradients to flow directly',
                    'Replacing fully connected layers with global average pooling',
                    'Using depthwise separable convolutions'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'ResNet introduces residual blocks where the input is added to the output of a few convolutional layers (F(x) + x). This allows gradients to flow directly through the skip connection, mitigating the vanishing gradient problem and enabling training of networks with 100+ layers.',
            },
            {
                'title': 'Recurrent Neural Networks and Transformers',
                'content_html': (
                    '<p>Sequence modeling requires handling variable-length inputs with temporal dependencies. '
                    'RNNs process sequences step by step, maintaining a hidden state. Transformers use '
                    'self-attention to process all positions in parallel, enabling massive scale.</p>'
                    '<p>This lesson covers RNNs, LSTMs, GRUs, and the vanishing gradient problem in long '
                    'sequences. We then introduce the Transformer architecture: self-attention, multi-head '
                    'attention, positional encoding, and the encoder-decoder structure. You\'ll see how BERT '
                    '(encoder-only) and GPT (decoder-only) adapt Transformers for language understanding and '
                    'generation, setting the stage for the LLMs & Agents module.</p>'
                ),
                'order': 4,
                'duration_minutes': 60,
            },
            {
                'title': 'Training Deep Networks: Best Practices',
                'content_html': (
                    '<p>Training deep networks effectively requires more than just choosing an architecture. '
                    'This lesson distills practical wisdom for getting models to converge and generalize.</p>'
                    '<p>Topics include: weight initialization (Xavier, He, Kaiming), batch normalization and '
                    'layer normalization, gradient clipping, learning rate scheduling (cosine annealing, '
                    'warmup, ReduceLROnPlateau), mixed precision training (AMP), gradient accumulation for '
                    'large effective batch sizes, early stopping, and model checkpointing. We also cover '
                    'debugging techniques: overfitting a single batch, gradient checking, and visualizing '
                    'activations and gradients.</p>'
                ),
                'order': 5,
                'duration_minutes': 50,
                'quiz_question': 'What is the purpose of gradient clipping in deep learning training?',
                'quiz_options': [
                    'To prevent the learning rate from becoming too large',
                    'To prevent exploding gradients by capping gradient magnitude',
                    'To clip the model weights to a fixed range',
                    'To clip the input data to prevent outliers'
                ],
                'quiz_correct_index': 1,
                'quiz_feedback': 'Gradient clipping caps the norm or value of gradients during backpropagation, preventing exploding gradients that can destabilize training, especially in RNNs and very deep networks. Common strategies: clip by value or clip by norm.',
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed courses and lessons for Cybersecurity and AI & Machine Learning career paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing course data for these careers before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing course data for Cybersecurity and AI & ML...')
            cyber_career = Career.objects.filter(slug='cyber').first()
            ai_career = Career.objects.filter(slug='ai').first()
            if cyber_career:
                Course.objects.filter(career=cyber_career).delete()
            if ai_career:
                Course.objects.filter(career=ai_career).delete()

        # Get career objects
        cyber_career = Career.objects.get(slug='cyber')
        ai_career = Career.objects.get(slug='ai')

        self.seed_career_courses(cyber_career, CYBERSECURITY_COURSES, 'Cybersecurity')
        self.seed_career_courses(ai_career, AI_ML_COURSES, 'AI & Machine Learning')

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded courses and lessons for both career paths')
        )

    def seed_career_courses(self, career, courses_data, career_name):
        for course_data in courses_data:
            lessons_data = course_data.pop('lessons')

            course, created = Course.objects.update_or_create(
                career=career,
                module_number=course_data['module_number'],
                order=course_data['order'],
                defaults={**course_data, 'is_published': True},
            )

            if created:
                self.stdout.write(f'  Created course: {career_name} - Module {course.module_number}: {course.title}')
            else:
                self.stdout.write(f'  Updated course: {career_name} - Module {course.module_number}: {course.title}')

            for lesson_data in lessons_data:
                lesson, lesson_created = Lesson.objects.update_or_create(
                    course=course,
                    order=lesson_data['order'],
                    defaults={**lesson_data, 'is_published': True},
                )

                if lesson_created:
                    quiz_info = ' (with quiz)' if lesson.has_quiz else ''
                    self.stdout.write(f'    Created lesson {lesson.order}: {lesson.title}{quiz_info}')