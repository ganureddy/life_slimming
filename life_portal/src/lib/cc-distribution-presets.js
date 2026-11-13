// Quick-start rules from the legacy Lead Distribution panel. They only fill the form.
export const distributionPresets = [
    { t: '⏱️ New lead in 15 min, best converter first', r: { rule_name: 'New lead not called', rule_type: 'Time-over New Lead', time_value: 15, time_unit: 'Minutes', method: 'Best Conversion' } },
    { t: '⏰ Follow-up late 4 hrs, most bookings first', r: { rule_name: 'Follow-up overdue', rule_type: 'Time-over Follow-up', time_value: 4, time_unit: 'Hours', method: 'Most Bookings' } },
    { t: '🚶 Follow-up late 1 day, quality walk-ins first', r: { rule_name: 'Follow-up 1 day late', rule_type: 'Time-over Follow-up', time_value: 1, time_unit: 'Days', method: 'Best Walk-ins' } },
    { t: '🚫 Agent absent, TL decides', r: { rule_name: 'Absent agent', rule_type: 'Absent Agent', absent_mode: 'Manual', method: 'Lowest Load', from_time: '10:30:00' } },
    { t: '🔥 Hot lead late 1 hr → free hands', hot: 1, r: { rule_name: 'Hot lead overdue 1 hr', rule_type: 'Hot Lead Overdue', time_value: 1, time_unit: 'Hours', method: 'Free Hands Follow-ups' } },
    { t: '🏥 Visited not booked → senior closers', r: { rule_name: 'Visited not booked to seniors', rule_type: 'Visited Not Booked', time_value: 1, time_unit: 'Hours', method: 'Best Conversion', senior: 1 } },
    { t: '🙌 New lead 15 min → agent with fewest leads', r: { rule_name: 'New lead to free hands', rule_type: 'Time-over New Lead', time_value: 15, time_unit: 'Minutes', method: 'Free Hands Leads' } }
  ];
