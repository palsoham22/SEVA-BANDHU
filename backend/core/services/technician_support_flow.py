"""
Centralized, deterministic decision-tree configuration for the Technician Support Assistant.

Provides structured categories, sub-options, troubleshooting steps, and escalation rules.
This guarantees reproducible, controllable support responses without relying on LLM generation.
"""

SUPPORT_CATEGORIES = {
    'PAYMENT_EARNINGS': {
        'key': 'PAYMENT_EARNINGS',
        'title': 'Payment / Earnings',
        'subtitle': 'Payouts, pending payments, completed job earnings, or fee calculations',
        'icon': 'cash',
        'badge': 'Financial',
        'requires_context': 'financial_choice',  # Can link service, wallet, or withdrawal
        'issues': {
            'missing_earnings': {
                'key': 'missing_earnings',
                'title': 'Missing earnings from completed job',
                'description': 'A completed job has not credited to your earnings or wallet balance',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Check Booking Completion Status',
                        'guidance': 'Please check whether the service booking is marked as "Completed" in your Assigned Jobs.\n\nEarnings are only credited once the job status transitions to "Completed" and the completion is registered on our server.',
                        'action_hint': 'Check "My Assigned Jobs" to confirm status shows Completed.',
                    },
                    {
                        'step': 2,
                        'title': 'Verify Settlement Window',
                        'guidance': 'If the customer paid online via UPI/Card, the payment gateway reconciliation may take between 30 minutes to 2 hours to settle into your wallet balance ledger.',
                        'action_hint': 'Check your Wallet ledger after the settlement window.',
                    },
                    {
                        'step': 3,
                        'title': 'Check for Customer Disputes or Deductions',
                        'guidance': 'Confirm if there are any active customer complaints, cancellation penalties, or warning points associated with this booking that might have put the credit on hold.',
                        'action_hint': 'Check your Warnings modal on the dashboard.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'payment_delayed': {
                'key': 'payment_delayed',
                'title': 'Payment delayed or payout pending',
                'description': 'Earnings or withdrawal payout is taking longer than expected',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Standard Banking Hours',
                        'guidance': 'Bank payouts are processed via NEFT/IMPS during standard banking hours. Transfers initiated on weekends, second/fourth Saturdays, or public holidays settle on the next business banking day.',
                        'action_hint': 'Allow up to 24-48 business hours for interbank settlement.',
                    },
                    {
                        'step': 2,
                        'title': 'Verify Bank Account Details',
                        'guidance': 'Please verify that your registered bank account number and IFSC code are accurate and belong to an active savings or current account.',
                        'action_hint': 'Check your profile bank information.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'completed_service_not_credited': {
                'key': 'completed_service_not_credited',
                'title': 'Completed service not credited to balance',
                'description': 'Specific booking was finished but balance remains unchanged',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Confirm Job Handshake',
                        'guidance': 'Ensure you tapped "Work Done / Completed" and received confirmation from the customer. If the job was left in "In Progress" status, earnings cannot be released.',
                        'action_hint': 'Verify job status is Completed.',
                    },
                    {
                        'step': 2,
                        'title': 'Refresh Wallet Ledger',
                        'guidance': 'Refresh your dashboard to fetch the latest server-side balance. If this job had cash payment collected on-site, cash payments are retained directly by you and platform commission is reconciled.',
                        'action_hint': 'Check if payment method was Cash or Online.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'incorrect_earnings': {
                'key': 'incorrect_earnings',
                'title': 'Incorrect earnings or deduction calculation',
                'description': 'Amount received differs from the booking rate or agreed quote',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Platform Fee Breakdown',
                        'guidance': 'Seva Bandhu deducts standard platform service commission (typically 10-15%) and applicable GST on digital services. The net amount credited reflects gross service fee minus platform charges.',
                        'action_hint': 'Calculate gross booking amount minus platform commission.',
                    },
                    {
                        'step': 2,
                        'title': 'Promotional Discounts or Offers',
                        'guidance': 'If a customer applied an authorized promotional coupon, platform subsidies are reconciled on your statement automatically.',
                        'action_hint': 'Check booking invoice details.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'other_payment_issue': {
                'key': 'other_payment_issue',
                'title': 'Other payment or earnings problem',
                'description': 'Any other payment inquiry or billing concern',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Verify Transaction Record',
                        'guidance': 'Review your recent transaction entries and match them against your active and completed service records.',
                        'action_hint': 'Locate the exact booking reference number.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'SERVICE_BOOKING': {
        'key': 'SERVICE_BOOKING',
        'title': 'Service / Booking',
        'subtitle': 'Assigned jobs, customer coordination, parts, cancellation, or schedule',
        'icon': 'briefcase',
        'badge': 'Operations',
        'requires_context': 'service',
        'issues': {
            'booking_issue': {
                'key': 'booking_issue',
                'title': 'Booking / Schedule conflict',
                'description': 'Time slot conflict, overlapping booking, or scheduling issue',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Customer Reschedule Request',
                        'guidance': 'If the customer is requesting a different date or time slot, you can coordinate directly with them using the in-app Customer Chat on the job card.',
                        'action_hint': 'Open Customer Chat from My Assigned Jobs.',
                    },
                    {
                        'step': 2,
                        'title': 'Emergency Overlap',
                        'guidance': 'If you have an emergency job overlap, prioritize the emergency booking and inform the other customer immediately via chat.',
                        'action_hint': 'Communicate expected arrival ETA.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'customer_issue': {
                'key': 'customer_issue',
                'title': 'Customer unreachable or address issue',
                'description': 'Customer not answering, incorrect address, or inaccessible site',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Verify Contact & Address',
                        'guidance': 'Check the flat number, street area, landmark, and phone number in the Service Address section of the booking. Try sending a message via the in-app customer chat.',
                        'action_hint': 'Call customer and send in-app message.',
                    },
                    {
                        'step': 2,
                        'title': 'Wait Window Protocol',
                        'guidance': 'Our standard policy requires waiting at the customer location for at least 15 minutes while attempting to contact them twice before reporting a customer no-show.',
                        'action_hint': 'Ensure GPS tracking is active to record arrival.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'service_issue': {
                'key': 'service_issue',
                'title': 'Service scope mismatch or parts required',
                'description': 'Job requires parts or scope is outside standard category service',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Provide Clear Quotation Before Commencing',
                        'guidance': 'If additional replacement parts (e.g. AC capacitor, copper piping, new valve) are needed, inform the customer of the parts cost and obtain verbal or chat consent prior to fitting.',
                        'action_hint': 'Record agreed parts price in customer chat.',
                    },
                    {
                        'step': 2,
                        'title': 'Safety or Trade Incompatibility',
                        'guidance': 'If the problem requires specialized equipment or hazardous handling beyond your licensed trade certification, do not proceed in an unsafe manner.',
                        'action_hint': 'Advise customer and request Admin reassignment.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'cancellation_issue': {
                'key': 'cancellation_issue',
                'title': 'Customer cancelled after arrival',
                'description': 'Customer cancelled booking on-site without prior notice',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Arrival Verification',
                        'guidance': 'If you traveled to the location and the customer cancelled on arrival, our policy provides a visiting fee compensation if live tracking was turned on during your transit.',
                        'action_hint': 'Ensure your job shows navigation/tracking was started.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'other_service': {
                'key': 'other_service',
                'title': 'Other booking or on-site issue',
                'description': 'Any other situation encountered during job assignment',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Standard Service Procedure',
                        'guidance': 'Please check the service instructions and make sure you have all details from the customer before escalating.',
                        'action_hint': 'Verify job notes.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'WALLET_WITHDRAWAL': {
        'key': 'WALLET_WITHDRAWAL',
        'title': 'Wallet / Withdrawal',
        'subtitle': 'Payout requests, bank transfers, failed transactions, or ledger discrepancies',
        'icon': 'credit-card',
        'badge': 'Payouts',
        'requires_context': 'withdrawal_or_wallet',
        'issues': {
            'wallet_balance_incorrect': {
                'key': 'wallet_balance_incorrect',
                'title': 'Wallet balance does not match expectations',
                'description': 'Discrepancy in current available wallet balance',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Deduct Pending Payouts',
                        'guidance': 'When you submit a withdrawal request, that requested amount is reserved immediately from your available wallet balance to prevent double payouts.',
                        'action_hint': 'Check if you have any "Pending" or "Processing" withdrawals.',
                    },
                    {
                        'step': 2,
                        'title': 'Check Adjustment Deductions',
                        'guidance': 'Verify if any penalty points or disputed refund chargebacks were applied by admin moderation.',
                        'action_hint': 'Review warnings modal.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'withdrawal_pending': {
                'key': 'withdrawal_pending',
                'title': 'Withdrawal marked Pending for over 48 hours',
                'description': 'Requested payout has not yet been processed by accounts',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Payout Processing Schedule',
                        'guidance': 'Admin accounts team processes batch payouts twice daily at 11:00 AM and 5:00 PM IST on working days. Bank clearance can take up to 24 hours depending on your recipient bank.',
                        'action_hint': 'Check the timestamp of your withdrawal submission.',
                    },
                    {
                        'step': 2,
                        'title': 'KYC and IFSC Verification',
                        'guidance': 'Ensure your bank account branch IFSC has not been modified due to bank mergers (e.g. Syndicate/Canara, Allahabad/Indian Bank).',
                        'action_hint': 'Confirm your IFSC matches current bank branch.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'withdrawal_failed': {
                'key': 'withdrawal_failed',
                'title': 'Withdrawal failed or rejected by bank',
                'description': 'Payout attempt was rejected or returned by the banking network',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Automatic Refund to Wallet',
                        'guidance': 'Whenever a bank payout is rejected by NPCI or the clearing house, the full amount is refunded automatically back into your Seva Bandhu wallet within 24 hours.',
                        'action_hint': 'Check your wallet balance for reversal credit.',
                    },
                    {
                        'step': 2,
                        'title': 'Correct Bank Details',
                        'guidance': 'Common reasons for failure include name mismatch between profile and bank passbook, invalid IFSC, or accounts frozen for dormant status.',
                        'action_hint': 'Verify account holder name exactly matches your bank record.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'withdrawal_amount_incorrect': {
                'key': 'withdrawal_amount_incorrect',
                'title': 'Amount received in bank is different from requested',
                'description': 'Transferred sum has deductions or charges',
                'steps': [
                    {
                        'step': 1,
                        'title': 'TDS & Payout Gateway Fees',
                        'guidance': 'Statutory 1% TDS under Section 194O of the Income Tax Act may be deducted for e-commerce service operators if your annual turnover exceeds applicable thresholds. Gateway fee of ₹5-10 applies on instant IMPS transfers.',
                        'action_hint': 'Check deduction breakdown on the payout statement.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'other_wallet_issue': {
                'key': 'other_wallet_issue',
                'title': 'Other wallet or withdrawal problem',
                'description': 'Any other financial or payout issue',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Locate Reference ID',
                        'guidance': 'Please have your bank transaction UTR or Seva Bandhu withdrawal request ID ready for faster resolution.',
                        'action_hint': 'Keep reference ID noted.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'INCENTIVE_REWARD': {
        'key': 'INCENTIVE_REWARD',
        'title': 'Incentive / Reward',
        'subtitle': '5-star bonuses, weekly top performer rewards, milestone missions',
        'icon': 'award',
        'badge': 'Rewards',
        'requires_context': 'incentive',
        'issues': {
            'incentive_not_credited': {
                'key': 'incentive_not_credited',
                'title': 'Earned incentive not credited to wallet',
                'description': 'Completed reward criteria but incentive bonus is missing',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Weekly Incentive Audit Cycle',
                        'guidance': 'Weekly mission and volume bonuses are audited on Sunday midnight and credited on Monday afternoons. If today is during the active week, please wait until the cycle closes.',
                        'action_hint': 'Check if current week cycle has completed.',
                    },
                    {
                        'step': 2,
                        'title': 'Minimum Rating Threshold',
                        'guidance': 'Incentive programs require maintaining an average customer rating of at least 4.5 stars and an acceptance rate of >= 85% throughout the week.',
                        'action_hint': 'Check your rating and job stats on the dashboard.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'mission_progress_incorrect': {
                'key': 'mission_progress_incorrect',
                'title': 'Mission / Milestone counter not updating',
                'description': 'Number of completed jobs in the current challenge looks wrong',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Eligible Booking Categories',
                        'guidance': 'Only jobs completed within your certified service category qualify for trade missions. Self-assigned test requests or cancelled bookings are excluded.',
                        'action_hint': 'Verify eligible completed jobs count.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'five_star_reward_missing': {
                'key': 'five_star_reward_missing',
                'title': '5-Star customer rating reward missing',
                'description': 'Received a 5-star customer review but reward was not registered',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Rating Verification Period',
                        'guidance': '5-star bonus incentives are verified through our automated fraud-prevention engine. Verified reviews award milestone credits on the subsequent payout batch.',
                        'action_hint': 'Check your total ratings count on dashboard.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'reward_calculation_issue': {
                'key': 'reward_calculation_issue',
                'title': 'Reward tier calculation issue',
                'description': 'Dispute regarding milestone tier or bonus rate',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Check Tier Requirements',
                        'guidance': 'Milestone rewards scale from Bronze (5 jobs), Silver (15 jobs), to Gold (30 jobs) per monthly cycle.',
                        'action_hint': 'Review the program criteria.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'other_incentive': {
                'key': 'other_incentive',
                'title': 'Other reward or recognition problem',
                'description': 'Any other inquiry regarding partner benefits',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Review Partner Benefits',
                        'guidance': 'Check current company campaign details in your partner portal notifications.',
                        'action_hint': 'Review recent partner announcements.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'APP_TECHNICAL': {
        'key': 'APP_TECHNICAL',
        'title': 'App / Technical Issue',
        'subtitle': 'GPS location, notifications, button clicks, browser, or app errors',
        'icon': 'smartphone',
        'badge': 'System',
        'requires_context': None,
        'issues': {
            'app_not_loading': {
                'key': 'app_not_loading',
                'title': 'App loading slowly or freezing',
                'description': 'Page fails to render or gets stuck on loading spinner',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Hard Refresh & Cache Clearing',
                        'guidance': 'Press Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac) to force a hard cache refresh. Alternatively, clear your browser cached files for this site.',
                        'action_hint': 'Press Ctrl + F5 or reload without cache.',
                    },
                    {
                        'step': 2,
                        'title': 'Browser Compatibility',
                        'guidance': 'Ensure you are using the latest version of Google Chrome, Microsoft Edge, or Safari. Turn off power-saving mode which can throttle background scripts.',
                        'action_hint': 'Try opening in an updated Chrome window.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'gps_tracking_issue': {
                'key': 'gps_tracking_issue',
                'title': 'GPS / Location tracking not updating',
                'description': 'Location cannot be retrieved or customer map cannot see movement',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Enable Browser Location Permission',
                        'guidance': 'Click the lock / settings icon next to the URL in your browser bar. Make sure "Location" is set to "Allow" instead of "Block" or "Ask".',
                        'action_hint': 'Check browser location permission prompt.',
                    },
                    {
                        'step': 2,
                        'title': 'Device Location Mode',
                        'guidance': 'On your mobile or laptop, ensure GPS / Location Services is turned ON in system settings and high accuracy is permitted.',
                        'action_hint': 'Toggle device GPS off and back on.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'notification_issue': {
                'key': 'notification_issue',
                'title': 'New request notifications not sounding or showing',
                'description': 'Missing customer requests or job sound alerts',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Sound & Autoplay Permissions',
                        'guidance': 'Browsers block audio alerts if the site does not have permission to play sound. Click anywhere on the dashboard after opening to enable audio context.',
                        'action_hint': 'Interact with dashboard page once after loading.',
                    },
                    {
                        'step': 2,
                        'title': 'Background Polling Active',
                        'guidance': 'Our dashboard features automatic dual fallback: live WebSockets and automatic 5-second polling. Keep the dashboard tab active or open in your browser.',
                        'action_hint': 'Do not minimize the dashboard tab.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'button_not_working': {
                'key': 'button_not_working',
                'title': 'Buttons or modals not responding to clicks',
                'description': 'Clicking an action does not trigger the expected modal or update',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Disable Ad-Blockers & Script Blockers',
                        'guidance': 'Extensions like uBlock, Brave Shields, or privacy extensions can sometimes intercept WebSocket packets or CSRF tokens. Whitelist Seva Bandhu.',
                        'action_hint': 'Temporarily disable ad-blockers on this domain.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'other_technical_issue': {
                'key': 'other_technical_issue',
                'title': 'Other technical problem',
                'description': 'Unexpected error message or system bug',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Take a Screenshot',
                        'guidance': 'If you see an error code or broken page, note what you were doing right before the issue occurred.',
                        'action_hint': 'Keep note of the exact error text.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'ACCOUNT_PROFILE': {
        'key': 'ACCOUNT_PROFILE',
        'title': 'Account / Profile',
        'subtitle': 'Trade skills, working cities, phone number, password, or verification status',
        'icon': 'user-check',
        'badge': 'Account',
        'requires_context': None,
        'issues': {
            'profile_info_problem': {
                'key': 'profile_info_problem',
                'title': 'Update working cities or years of experience',
                'description': 'Need to modify profile details or contact information',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Use Profile Modal',
                        'guidance': 'Click your profile avatar in the top right corner of the dashboard and select "Complete / Edit Profile". You can edit working cities, experience, and contact details directly.',
                        'action_hint': 'Open Profile Modal from dashboard avatar.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'category_change': {
                'key': 'category_change',
                'title': 'Change registered trade category',
                'description': 'Switch between AC Repair, Electrical, Plumbing, or Cleaning',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Admin Verification Required',
                        'guidance': 'To protect service quality and customer safety, changing your core trade category requires verification of your skills certification by an Admin.',
                        'action_hint': 'Contact Admin to submit trade change request.',
                    }
                ],
                'escalation_threshold': 1,
            },
            'warning_status_inquiry': {
                'key': 'warning_status_inquiry',
                'title': 'Review or dispute warning penalty points',
                'description': 'Inquire about a penalty point or customer complaint warning',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Inspect Warning Details',
                        'guidance': 'Click the "Warnings" badge on your dashboard to see the exact reason, date, and associated customer complaint for each penalty.',
                        'action_hint': 'Open Warnings modal from dashboard.',
                    },
                    {
                        'step': 2,
                        'title': 'Warning Expiry & Performance Recovery',
                        'guidance': 'Penalty points automatically decrease over time as you complete more positive 5-star jobs with zero new customer complaints.',
                        'action_hint': 'Maintain high service ratings to offset penalties.',
                    }
                ],
                'escalation_threshold': 2,
            },
            'other_account_issue': {
                'key': 'other_account_issue',
                'title': 'Other account or login problem',
                'description': 'General account management inquiry',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Check Account Availability Toggle',
                        'guidance': 'Ensure your status is set to Available on the dashboard to receive new incoming service requests.',
                        'action_hint': 'Verify you are toggled online.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    },

    'OTHER': {
        'key': 'OTHER',
        'title': 'Other',
        'subtitle': 'Any other topic, specialized inquiry, or direct Admin request',
        'icon': 'message-circle',
        'badge': 'General',
        'requires_context': 'custom_input',
        'issues': {
            'custom_inquiry': {
                'key': 'custom_inquiry',
                'title': 'Custom issue or question',
                'description': 'Describe your issue in your own words',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Self-Check Guidelines',
                        'guidance': 'Please provide a short summary of the issue so we can direct you to the right solution or connect you with the appropriate Admin team member.',
                        'action_hint': 'Type a brief summary in the chat input.',
                    }
                ],
                'escalation_threshold': 1,
            }
        }
    }
}


def get_categories_list():
    """Return a clean list of category summaries for button rendering."""
    categories = []
    for cat_key, cat_data in SUPPORT_CATEGORIES.items():
        categories.append({
            'key': cat_key,
            'title': cat_data['title'],
            'subtitle': cat_data['subtitle'],
            'icon': cat_data['icon'],
            'badge': cat_data['badge'],
            'requires_context': cat_data.get('requires_context'),
            'issue_count': len(cat_data['issues']),
        })
    return categories


def get_category_issues(category_key):
    """Return issues available under a specific category."""
    cat = SUPPORT_CATEGORIES.get(category_key)
    if not cat:
        return []
    issues = []
    for issue_key, issue_data in cat['issues'].items():
        issues.append({
            'key': issue_key,
            'title': issue_data['title'],
            'description': issue_data['description'],
            'step_count': len(issue_data['steps']),
            'escalation_threshold': issue_data.get('escalation_threshold', 2),
        })
    return issues


def get_issue_details(category_key, issue_key):
    """Return full issue definition including all troubleshooting steps."""
    cat = SUPPORT_CATEGORIES.get(category_key)
    if not cat:
        return None
    return cat['issues'].get(issue_key)

