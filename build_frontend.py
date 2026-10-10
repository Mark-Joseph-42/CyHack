#!/usr/bin/env python3
"""
build_frontend.py
Builds:
1. frontend/buyer.html (Buyer View wired to /api/properties & /api/leads/chat)
2. frontend/broker.html (Broker View wired to /api/leads & /api/qualifications)
3. frontend/index.html (Unified switcher landing page)
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STITCH_DIR = os.path.join(
    FRONTEND_DIR,
    "stitch_real_estate_lead_qualifier(1)",
    "stitch_real_estate_lead_qualifier"
)

BUYER_SRC = os.path.join(STITCH_DIR, "buyer_discovery_full_width_matches_with_on_demand_concierge", "code.html")
BROKER_SRC = os.path.join(STITCH_DIR, "brokerdesk_pro_master_detail_lead_intelligence", "code.html")

BUYER_DEST = os.path.join(FRONTEND_DIR, "buyer.html")
BROKER_DEST = os.path.join(FRONTEND_DIR, "broker.html")
INDEX_DEST = os.path.join(FRONTEND_DIR, "index.html")


def build_buyer():
    print(f"🔨 Building {BUYER_DEST}...")
    with open(BUYER_SRC, "r", encoding="utf-8") as f:
        html = f.read()

    # Link switcher button to broker.html
    html = html.replace('href="#discovery-view"', 'href="buyer.html"')
    html = html.replace('href="#broker-view"', 'href="broker.html"')

    nav_switch_btn = '''
    <a href="broker.html" class="flex items-center gap-1.5 bg-secondary text-surface-container-lowest hover:bg-secondary/90 px-3.5 py-1.5 rounded-lg text-label-mono-sm font-label-mono-sm font-bold shadow-sm transition-all mr-2">
      <span class="material-symbols-outlined text-[16px]">dashboard</span>
      <span>Broker Dashboard →</span>
    </a>
    '''
    target_anchor = '<button aria-label="Notifications"'
    if target_anchor in html:
        html = html.replace(target_anchor, nav_switch_btn + target_anchor)

    # Dynamic JavaScript to wire properties and live chat
    dynamic_js = '''
<script>
// =====================================================================
// Real-Time API Integration for Buyer Discovery & AI Concierge
// =====================================================================
const API_BASE = window.location.origin.includes('http') ? '' : 'http://127.0.0.1:8000';
let activeLeadId = 1; // Marcus Vance by default
let allProperties = [];

const propertyImages = {
  1: "https://lh3.googleusercontent.com/aida-public/AB6AXuDNqwXFuAA5K8719npMGIXotlOE6XFTN4JYPE5-BZMY4fQmo-tIoqg2hzgNBjrVj3pGKLM-eh0hSI983AuwYMd7RWtQdXOLIQeAzbS5vtl1IY53jzqneWcZUXmja0VVoVoF6aGhaNMvc723Jg-rcF8T3Qs-QX0wCkmK_7Xy120LRkRBgnRkV_EUiDIS9_ewfEzv5GJBWaince1fSCqlITDttVYnhBpgbBy0AkRGST3TjJ9MzqHoWpim0A",
  2: "https://lh3.googleusercontent.com/aida-public/AB6AXuAACGiv-0dep3WDQgjurqBK0ofxumyMYw9yIHdV5ovTGq7OjDBdVXZdydY3HFMqOnWn2ybiz_bzHD-c-oKSYcWxm1beAmYJczAQuRumH0QuWTRnbULxzJ9qkfr0quTocunj54sLW9j-dB66a2YxFnUCqhL8dz90wFq19IlCd-Oawb8u73RO0-k1XAcFDZALl47G1H4YmQXvvmZWLAeDBAm_J3NrvgE8KjGnXQlmM32fNtIjx8-pRBs9Zw",
  3: "https://lh3.googleusercontent.com/aida-public/AB6AXuDNqwXFuAA5K8719npMGIXotlOE6XFTN4JYPE5-BZMY4fQmo-tIoqg2hzgNBjrVj3pGKLM-eh0hSI983AuwYMd7RWtQdXOLIQeAzbS5vtl1IY53jzqneWcZUXmja0VVoVoF6aGhaNMvc723Jg-rcF8T3Qs-QX0wCkmK_7Xy120LRkRBgnRkV_EUiDIS9_ewfEzv5GJBWaince1fSCqlITDttVYnhBpgbBy0AkRGST3TjJ9MzqHoWpim0A",
  4: "https://lh3.googleusercontent.com/aida-public/AB6AXuAACGiv-0dep3WDQgjurqBK0ofxumyMYw9yIHdV5ovTGq7OjDBdVXZdydY3HFMqOnWn2ybiz_bzHD-c-oKSYcWxm1beAmYJczAQuRumH0QuWTRnbULxzJ9qkfr0quTocunj54sLW9j-dB66a2YxFnUCqhL8dz90wFq19IlCd-Oawb8u73RO0-k1XAcFDZALl47G1H4YmQXvvmZWLAeDBAm_J3NrvgE8KjGnXQlmM32fNtIjx8-pRBs9Zw",
  5: "https://lh3.googleusercontent.com/aida-public/AB6AXuDNqwXFuAA5K8719npMGIXotlOE6XFTN4JYPE5-BZMY4fQmo-tIoqg2hzgNBjrVj3pGKLM-eh0hSI983AuwYMd7RWtQdXOLIQeAzbS5vtl1IY53jzqneWcZUXmja0VVoVoF6aGhaNMvc723Jg-rcF8T3Qs-QX0wCkmK_7Xy120LRkRBgnRkV_EUiDIS9_ewfEzv5GJBWaince1fSCqlITDttVYnhBpgbBy0AkRGST3TjJ9MzqHoWpim0A"
};

async function fetchProperties() {
  try {
    const res = await fetch(`${API_BASE}/api/properties`);
    if (res.ok) {
      allProperties = await res.json();
      renderPropertiesList(allProperties);
    }
  } catch (e) {
    console.warn('Backend API offline, retaining static properties:', e);
  }
}

function renderPropertiesList(props) {
  const container = document.querySelector('.grid.grid-cols-1.md\\\\:grid-cols-2.lg\\\\:grid-cols-3');
  if (!container || !props || props.length === 0) return;

  container.innerHTML = props.map((p, idx) => {
    const imgUrl = propertyImages[p.id] || propertyImages[1];
    const matchPct = 98 - (idx * 4);
    const estMo = Math.round(p.price * 0.0048);
    return `
      <article class="bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden shadow-sm flex flex-col group hover:border-secondary hover:shadow-md transition-all duration-300 relative" data-property-id="${p.id}">
        <div class="relative h-56 w-full overflow-hidden bg-surface-container">
          <img alt="${p.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" src="${imgUrl}">
          <div class="absolute inset-0 bg-gradient-to-t from-primary/80 via-transparent to-transparent"></div>
          <div class="absolute top-3 left-3 flex flex-wrap gap-1.5">
            <span class="bg-primary text-secondary-fixed text-label-mono-sm font-label-mono-sm px-2.5 py-0.5 rounded font-bold border border-secondary-fixed flex items-center gap-1 shadow-sm">
              <span class="material-symbols-outlined text-[14px] text-secondary-fixed">verified</span> ${matchPct}% Match
            </span>
            ${idx === 0 ? '<span class="bg-secondary-fixed text-on-secondary-fixed text-label-mono-sm font-label-mono-sm px-2 py-0.5 rounded font-bold shadow-sm">Top Pick</span>' : ''}
          </div>
          <div class="absolute bottom-3 left-3 right-3 flex items-end justify-between text-surface-container-lowest">
            <div>
              <div class="text-label-mono-sm font-label-mono-sm text-secondary-fixed tracking-wide uppercase font-bold text-[10px]">${p.property_type || 'Residence'}</div>
              <div class="text-headline-sm font-headline-sm font-bold text-surface-container-lowest">$${p.price.toLocaleString()}</div>
            </div>
            <div class="text-label-mono-sm font-label-mono-sm bg-primary/80 px-2 py-1 rounded text-surface-container-lowest text-[11px]">
              Est. $${estMo.toLocaleString()} / mo
            </div>
          </div>
        </div>
        <div class="p-space-md flex-1 flex flex-col justify-between space-y-space-xs">
          <div class="space-y-1.5">
            <div class="flex items-center gap-1 text-on-surface-variant text-body-sm font-body-sm">
              <span class="material-symbols-outlined text-[15px] text-secondary">location_on</span>
              <span class="font-semibold text-primary truncate">${p.location}</span>
            </div>
            <h3 class="text-headline-sm font-headline-sm font-bold text-primary leading-snug line-clamp-2">${p.title}</h3>
            <p class="text-body-sm text-on-surface-variant line-clamp-2 text-xs">${p.description || 'Exclusive prime property in sought-after neighborhood.'}</p>
            <div class="grid grid-cols-3 gap-2 py-2 px-2.5 bg-surface rounded-lg border border-outline-variant text-center my-2">
              <div>
                <span class="text-on-surface-variant block text-[10px] uppercase font-medium">Bedrooms</span>
                <span class="text-body-md font-semibold text-primary">${p.bedrooms} Beds</span>
              </div>
              <div class="border-x border-outline-variant">
                <span class="text-on-surface-variant block text-[10px] uppercase font-medium">Status</span>
                <span class="text-body-md font-semibold text-secondary">Available</span>
              </div>
              <div>
                <span class="text-on-surface-variant block text-[10px] uppercase font-medium">Price / SqFt</span>
                <span class="text-body-md font-semibold text-primary">$345</span>
              </div>
            </div>
          </div>
          <div class="pt-2 flex items-center gap-2">
            <button onclick="selectPropertyForTour('${p.title}', ${p.price})" class="flex-1 bg-secondary text-surface-container-lowest hover:bg-secondary/90 py-2.5 px-3 rounded-lg font-semibold text-body-sm flex items-center justify-center gap-1.5 shadow-sm transition-all">
              <span class="material-symbols-outlined text-[16px]">calendar_month</span>
              <span>Request Viewing</span>
            </button>
            <button onclick="selectPropertyForAi('${p.title}', ${p.price})" class="flex-1 bg-surface-container-high hover:bg-surface-container text-primary py-2.5 px-3 rounded-lg font-semibold text-body-sm flex items-center justify-center gap-1.5 transition-all border border-outline-variant">
              <span class="material-symbols-outlined text-[16px]">chat</span>
              <span>Ask AI</span>
            </button>
          </div>
        </div>
      </article>
    `;
  }).join('');
}

function selectPropertyForTour(title, price) {
  const titleEl = document.getElementById('activePropertyTitle');
  const priceEl = document.getElementById('activePropertyPrice');
  if (titleEl) titleEl.textContent = title;
  if (priceEl) priceEl.textContent = '$' + price.toLocaleString();

  const chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.value = `I would like to request an immediate viewing for ${title} ($${price.toLocaleString()}). I have pre-approved financing.`;
    chatInput.focus();
  }
}

function selectPropertyForAi(title, price) {
  selectPropertyForTour(title, price);
  const chatForm = document.getElementById('chatForm');
  if (chatForm) {
    chatForm.dispatchEvent(new Event('submit'));
  }
}

// Live Chat Handlers
document.addEventListener('DOMContentLoaded', () => {
  fetchProperties();

  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatThread = document.getElementById('chatThread');

  if (chatForm && chatInput && chatThread) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;

      // Append User message to UI
      const userBubble = document.createElement('div');
      userBubble.className = 'flex items-start justify-end gap-space-sm';
      userBubble.innerHTML = `
        <div class="bg-primary-container text-surface-container-lowest rounded-xl rounded-tr-none p-3 shadow-sm max-w-[85%] space-y-1">
          <p class="leading-relaxed">${message}</p>
          <span class="text-label-mono-sm font-label-mono-sm text-on-primary-container block text-right text-[10px]">Just now</span>
        </div>
        <div class="w-8 h-8 rounded-full bg-secondary text-surface-container-lowest flex items-center justify-center shrink-0 mt-0.5 font-bold text-label-mono-sm">
          MV
        </div>
      `;
      chatThread.appendChild(userBubble);
      chatInput.value = '';
      chatThread.scrollTop = chatThread.scrollHeight;

      // Show typing indicator
      const typingEl = document.createElement('div');
      typingEl.id = 'typingIndicator';
      typingEl.className = 'flex items-start gap-space-sm text-outline';
      typingEl.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-primary-container text-secondary-fixed flex items-center justify-center shrink-0 mt-0.5">
          <span class="material-symbols-outlined text-[16px] animate-spin">sync</span>
        </div>
        <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-2.5 text-xs text-outline italic">
          AI Concierge analyzing preferences & inventory...
        </div>
      `;
      chatThread.appendChild(typingEl);
      chatThread.scrollTop = chatThread.scrollHeight;

      try {
        const response = await fetch(`${API_BASE}/api/leads/${activeLeadId}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        typingEl.remove();

        const aiBubble = document.createElement('div');
        aiBubble.className = 'flex items-start gap-space-sm';
        aiBubble.innerHTML = `
          <div class="w-8 h-8 rounded-full bg-primary-container text-secondary-fixed flex items-center justify-center shrink-0 mt-0.5">
            <span class="material-symbols-outlined text-[16px]">smart_toy</span>
          </div>
          <div class="bg-surface-container-lowest border border-outline-variant rounded-xl rounded-tl-none p-3 shadow-sm max-w-[88%] text-on-surface space-y-2">
            <p class="leading-relaxed">${data.reply}</p>
            ${data.decision ? `
              <div class="bg-secondary-container/30 border border-secondary rounded-lg p-2 flex items-center justify-between text-xs">
                <span class="font-bold text-secondary">Underwriting Score: ${data.decision.qualification_score}/100</span>
                <span class="px-2 py-0.5 bg-secondary text-surface-container-lowest rounded text-[10px] font-bold">ACTION: ${data.decision.next_action}</span>
              </div>
            ` : ''}
            <span class="text-label-mono-sm font-label-mono-sm text-outline block text-right text-[10px]">Just now</span>
          </div>
        `;
        chatThread.appendChild(aiBubble);
        chatThread.scrollTop = chatThread.scrollHeight;
      } catch (err) {
        typingEl.remove();
        console.error('Chat error:', err);
      }
    });
  }

  // Quick chip click handlers
  document.querySelectorAll('.chat-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.querySelector('span:last-child')?.textContent;
      if (text && chatInput) {
        chatInput.value = text;
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // Filter input listeners
  const locationInput = document.querySelector('input[placeholder*="Downtown"]');
  const budgetSlider = document.querySelector('input[type="range"]');
  const budgetDisplay = document.querySelector('.text-secondary.font-bold');

  if (budgetSlider && budgetDisplay) {
    budgetSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value) * 1000;
      budgetDisplay.textContent = '$' + val.toLocaleString();
      filterPropertiesDynamically(locationInput ? locationInput.value : '', val);
    });
  }

  if (locationInput) {
    locationInput.addEventListener('input', (e) => {
      const budgetVal = budgetSlider ? parseInt(budgetSlider.value) * 1000 : 9999999;
      filterPropertiesDynamically(e.target.value, budgetVal);
    });
  }

  function filterPropertiesDynamically(loc, maxPrice) {
    if (!allProperties || allProperties.length === 0) return;
    const filtered = allProperties.filter(p => {
      const matchLoc = !loc || p.location.toLowerCase().includes(loc.toLowerCase().trim());
      const matchPrice = !maxPrice || p.price <= (maxPrice * 1.15);
      return matchLoc && matchPrice;
    });
    renderPropertiesList(filtered.length > 0 ? filtered : allProperties);
  }
});
</script>
'''
    html = html.replace('</body>', dynamic_js + '\n</body>')

    with open(BUYER_DEST, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Created frontend/buyer.html")


def build_broker():
    print(f"🔨 Building {BROKER_DEST}...")
    with open(BROKER_SRC, "r", encoding="utf-8") as f:
        html = f.read()

    # Link return to buyer discovery
    html = html.replace('href="#discovery-view"', 'href="buyer.html"')

    # Dynamic JavaScript for BrokerDesk Pro
    dynamic_broker_js = '''
<script>
// =====================================================================
// Real-Time API Integration for BrokerDesk Pro Dashboard
// =====================================================================
const API_BASE = window.location.origin.includes('http') ? '' : 'http://127.0.0.1:8000';
let allLeads = [];
let currentFilter = 'ALL'; // ALL, CALL_UP, NEGOTIATE
let selectedLeadId = 1;

async function loadBrokerData() {
  try {
    const res = await fetch(`${API_BASE}/api/leads`);
    if (res.ok) {
      allLeads = await res.json();
      renderLeadDirectory();
      if (allLeads.length > 0) {
        selectLead(allLeads[0].id);
      }
    }
  } catch (err) {
    console.warn('API connection failed, falling back to static:', err);
  }
}

function renderLeadDirectory() {
  const listContainer = document.querySelector('.flex-1.overflow-y-auto.custom-scrollbar.divide-y');
  if (!listContainer || !allLeads) return;

  const filtered = allLeads.filter(l => {
    if (currentFilter === 'ALL') return true;
    return l.qualification && l.qualification.next_action === currentFilter;
  });

  listContainer.innerHTML = filtered.map(lead => {
    const q = lead.qualification || {};
    const action = q.next_action || 'AMBIGUOUS';
    const score = q.qualification_score !== undefined ? Math.round(q.qualification_score) : 50;
    const isSelected = lead.id === selectedLeadId;
    const isCallUp = action === 'CALL_UP';
    const badgeColor = isCallUp ? 'bg-secondary text-on-secondary' : 'bg-tertiary-fixed/30 text-tertiary-container border border-tertiary-fixed-dim';
    const dotColor = isCallUp ? 'bg-secondary' : 'bg-tertiary-fixed-dim';
    const propTitle = (q.matched_property && q.matched_property.title) || 'General Portfolio';
    const propPrice = (q.matched_property && q.matched_property.price) ? `$${q.matched_property.price.toLocaleString()}` : '$850,000';

    return `
      <div onclick="selectLead(${lead.id})" class="p-3 ${isSelected ? 'bg-secondary-container/15 border-l-4 border-secondary' : 'hover:bg-surface-container'} cursor-pointer relative transition-colors">
        <div class="flex items-start justify-between gap-1">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full ${dotColor} shrink-0"></span>
            <span class="text-body-md font-body-md font-bold text-primary">${lead.name}</span>
          </div>
          <span class="px-1.5 py-0.5 ${badgeColor} rounded text-[10px] font-label-mono-sm font-bold uppercase tracking-wider">
            ${action} · ${score}
          </span>
        </div>
        <div class="text-body-sm font-body-sm text-primary font-medium mt-1 truncate flex items-center gap-1">
          <span class="material-symbols-outlined text-xs text-outline">apartment</span>
          ${propTitle}
        </div>
        <div class="flex items-center justify-between text-body-sm text-on-surface-variant mt-0.5">
          <span class="font-label-mono-sm text-secondary font-bold text-xs">${propPrice}</span>
          <span class="text-[11px] text-outline font-label-mono-sm">Verified</span>
        </div>
        <div class="flex items-center gap-1.5 mt-2 flex-wrap">
          <span class="px-1.5 py-0.2 bg-surface-container-low text-on-surface text-[10px] font-label-mono-sm rounded border border-outline-variant/60">
            ${q.timeline_months ? `< ${q.timeline_months * 30} Days` : 'Urgent'}
          </span>
          <span class="px-1.5 py-0.2 bg-surface-container-low text-secondary text-[10px] font-label-mono-sm rounded border border-outline-variant/60 font-semibold">
            ${lead.status}
          </span>
        </div>
      </div>
    `;
  }).join('');
}

function selectLead(leadId) {
  selectedLeadId = leadId;
  renderLeadDirectory();

  const lead = allLeads.find(l => l.id === leadId);
  if (!lead) return;

  const q = lead.qualification || {};
  const prop = q.matched_property || {};

  // Header updates
  const nameEl = document.querySelector('section[aria-label*="Client Dossier"] h2');
  if (nameEl) nameEl.textContent = lead.name;

  const scoreBadge = document.querySelector('section[aria-label*="Client Dossier"] .bg-secondary.text-on-secondary.rounded');
  if (scoreBadge) scoreBadge.textContent = `${lead.status} ${Math.round(q.qualification_score || 0)}/100`;

  const actionBadge = document.querySelector('section[aria-label*="Client Dossier"] .bg-secondary-container\\\\/40');
  if (actionBadge) actionBadge.textContent = `ACTION: ${q.next_action || 'UNDERWRITING'}`;

  // Contact links
  const emailLink = document.querySelector('a[href^="mailto:"]');
  if (emailLink) {
    emailLink.href = `mailto:${lead.email || 'lead@example.com'}`;
    emailLink.textContent = lead.email || 'lead@example.com';
  }

  const phoneLink = document.querySelector('a[href^="tel:"]');
  if (phoneLink) {
    const phone = lead.phone || '+1 (555) 0192';
    phoneLink.href = `tel:${phone}`;
    phoneLink.textContent = `${phone} (Direct Cell)`;
  }

  // Matched property
  const propTitleEl = document.querySelector('section[aria-label*="Client Dossier"] .text-headline-sm.text-base');
  if (propTitleEl) propTitleEl.textContent = prop.title || 'Portfolio Inquiry';

  const askingEl = document.querySelectorAll('section[aria-label*="Client Dossier"] .text-headline-sm.font-bold')[1];
  if (askingEl && prop.price) askingEl.textContent = `$${prop.price.toLocaleString()}`;

  const budgetEl = document.querySelectorAll('section[aria-label*="Client Dossier"] .text-headline-sm.font-bold')[2];
  if (budgetEl && q.budget_max) budgetEl.textContent = `$${q.budget_max.toLocaleString()}`;

  // AI Reasoning
  const rationaleEl = document.querySelector('section[aria-label*="Client Dossier"] p.italic');
  if (rationaleEl && q.decision_reasoning) {
    rationaleEl.textContent = `“${q.decision_reasoning}”`;
  }

  // Conversation transcripts
  const chatContainer = document.querySelector('section[aria-label*="Client Dossier"] .space-y-2\\\\.5');
  if (chatContainer && lead.conversation_logs) {
    chatContainer.innerHTML = lead.conversation_logs.map(log => {
      const isAi = log.sender === 'AI Agent' || log.sender === 'AI';
      if (isAi) {
        return `
          <div class="flex items-start gap-2.5">
            <div class="w-6 h-6 rounded bg-primary text-secondary-fixed flex items-center justify-center shrink-0 text-xs font-bold">AI</div>
            <div class="bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/60 max-w-[85%]">
              <div class="text-[10px] text-outline font-label-mono-sm mb-0.5">AI Concierge</div>
              <p class="text-body-sm">${log.message_text}</p>
            </div>
          </div>
        `;
      } else {
        return `
          <div class="flex items-start gap-2.5 justify-end">
            <div class="bg-primary text-on-primary p-2 rounded-lg max-w-[85%] text-right">
              <div class="text-[10px] text-secondary-fixed font-label-mono-sm mb-0.5">${lead.name}</div>
              <p class="text-left text-body-sm">${log.message_text}</p>
            </div>
            <div class="w-6 h-6 rounded bg-secondary text-on-secondary flex items-center justify-center shrink-0 text-xs font-bold">
              ${lead.name.split(' ').map(n => n[0]).join('')}
            </div>
          </div>
        `;
      }
    }).join('');
  }
}

// Setup Triage Filter Button listeners
document.addEventListener('DOMContentLoaded', () => {
  loadBrokerData();

  const filterButtons = document.querySelectorAll('section[aria-label*="Client Pipeline"] button');
  filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      filterButtons.forEach(b => {
        b.className = 'px-2.5 py-1 bg-surface-container-low text-on-surface-variant hover:bg-surface-container rounded border border-outline-variant/70 font-medium transition-colors';
      });
      btn.className = 'px-2.5 py-1 bg-primary text-on-primary rounded font-bold shadow-xs';

      const label = btn.textContent.toLowerCase();
      if (label.includes('call-up')) {
        currentFilter = 'CALL_UP';
      } else if (label.includes('negotiate')) {
        currentFilter = 'NEGOTIATE';
      } else {
        currentFilter = 'ALL';
      }
      renderLeadDirectory();
    });
  });
});
</script>
'''

    html = html.replace('</body>', dynamic_broker_js + '\n</body>')

    with open(BROKER_DEST, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Created frontend/broker.html")


def build_index():
    print(f"🔨 Building {INDEX_DEST}...")
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PrimeEstates Pro — Real Estate Lead Qualifier</title>
  <meta http-equiv="refresh" content="0; url=buyer.html">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white flex items-center justify-center min-h-screen">
  <div class="text-center space-y-4">
    <h1 class="text-3xl font-bold">PrimeEstates Pro</h1>
    <p class="text-slate-400">Loading Buyer Discovery & AI Concierge...</p>
    <div class="flex gap-4 justify-center pt-2">
      <a href="buyer.html" class="px-4 py-2 bg-emerald-500 rounded font-semibold text-black">Buyer Discovery View</a>
      <a href="broker.html" class="px-4 py-2 bg-slate-700 rounded font-semibold">Broker Dashboard</a>
    </div>
  </div>
</body>
</html>
'''
    with open(INDEX_DEST, "w", encoding="utf-8") as f:
        f.write(index_html)
    print("✅ Created frontend/index.html")


if __name__ == "__main__":
    build_buyer()
    build_broker()
    build_index()
    print("🎉 All frontend views built and wired successfully!")
