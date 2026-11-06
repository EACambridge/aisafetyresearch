// Shared sign-in helpers for AI Safety Research pages
(function () {
  var configured = window.SUPABASE_URL && window.SUPABASE_URL.indexOf("PASTE_") !== 0;
  window.asr = {
    configured: configured,
    client: configured ? window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY) : null,
    esc: function (s) {
      return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    },
    session: async function () {
      if (!this.client) return null;
      var r = await this.client.auth.getSession();
      return r.data.session;
    },
    log: async function (type, details) {
      var s = await this.session();
      if (!s) return;
      await this.client.from("events").insert({ user_id: s.user.id, type: type, details: details || null });
    },
    notConfigured: function (el) {
      el.innerHTML = '<p class="msg">Accounts aren’t switched on yet. Please check back soon.</p>';
    }
  };
})();
