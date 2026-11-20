// Shared code for comments on completed projects and forum threads. Posts go live straight away; admins can remove them.
// Needs supabase-js, supabase-config.js and auth.js loaded first.
(function () {
  var esc = function (s) { return window.asr.esc(s); };

  function when(d) {
    return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  }

  // Plain text in, safe HTML out: paragraphs, line breaks and clickable https links.
  function prose(text) {
    return String(text || "").trim().split(/\n\s*\n/).map(function (para) {
      var html = esc(para).replace(/\n/g, "<br>");
      html = html.replace(/https:\/\/[^\s<]+[^\s<.,;:!?)\]]/g, function (u) {
        return '<a href="' + u + '" rel="nofollow ugc noopener">' + u + "</a>";
      });
      return "<p>" + html + "</p>";
    }).join("");
  }

  // Where to come back to after signing in.
  function signInLink(text) {
    var here = location.pathname.split("/").pop() + location.search;
    return '<a class="secondary" href="login.html?next=' + encodeURIComponent(here) + '">' + esc(text) + "</a>";
  }

  async function me() {
    if (!window.asr || !asr.configured) return null;
    var s = await asr.session();
    if (!s) return null;
    var out = { id: s.user.id, name: "A member", admin: false };
    var p = await asr.client.from("profiles").select("full_name,name_visibility").eq("id", s.user.id).maybeSingle();
    if (p.data) {
      var full = String(p.data.full_name || "").trim();
      if (p.data.name_visibility === "full" && full) out.name = full;
      else if (p.data.name_visibility === "first" && full) out.name = full.split(" ")[0];
    }
    var a = await asr.client.rpc("is_admin");
    out.admin = !!a.data;
    return out;
  }

  async function rpc(fn, args) {
    if (!window.asr || !asr.configured) return [];
    var r = await asr.client.rpc(fn, args || {});
    return r.data || [];
  }

  // Renders the comments and comment box for one project ({post: id}) or thread ({thread: id}).
  async function comments(box, target, user, words) {
    words = words || { one: "comment", many: "comments", add: "Add a comment", button: "Post comment", none: "No comments yet." };
    var key = target.post ? "post_id" : "thread_id";
    var id = target.post || target.thread;
    async function load() {
      var shown = await rpc("public_comments", target.post ? { pid: id } : { tid: id });
      var mine = [];
      if (user) {
        var r = await asr.client.from("comments").select("id,body,created_at,status").eq(key, id).eq("user_id", user.id).neq("status", "approved").order("created_at");
        mine = r.data || [];
      }
      var items = shown.map(function (c) {
        return '<li><div class="who">' + esc(c.author) + ' <span class="meta">' + when(c.created_at) + "</span></div>" + prose(c.body) +
          (user && user.admin ? '<button class="link" data-hide-comment="' + c.id + '">Remove</button>' : "") + "</li>";
      }).concat(mine.map(function (c) {
        return '<li class="pending"><div class="who">You <span class="meta">' + when(c.created_at) + ", " +
          (c.status === "pending" ? "waiting for approval" : "removed by an organiser") + "</span></div>" + prose(c.body) +
          '<button class="link" data-del-comment="' + c.id + '">Delete</button></li>';
      }));
      box.querySelector(".comment-list").innerHTML = items.length ? items.join("") : '<li class="none">' + words.none + "</li>";
      box.querySelector(".comment-count").textContent = shown.length === 1 ? "1 " + words.one : shown.length + " " + words.many;
    }

    box.innerHTML = '<h2 class="comment-count">' + words.many.charAt(0).toUpperCase() + words.many.slice(1) + '</h2><ul class="comments comment-list"><li class="none">Loading…</li></ul>' +
      (user
        ? '<form class="comment-form"><label for="comment-body">' + words.add + '</label>' +
          '<textarea id="comment-body" maxlength="3000" required placeholder="Questions, suggestions, related work, encouragement…"></textarea>' +
          '<p class="hint">You’ll appear as <strong>' + esc(user.name) + '</strong> (change this on <a href="account.html">your account</a>). ' +
          "Your comment appears straight away. Please be kind and specific.</p>" +
          '<button type="submit">' + words.button + '</button><div class="form-status" aria-live="polite"></div></form>'
        : '<p class="signin">' + signInLink("Sign in to " + (words.one === "reply" ? "reply" : "comment")) + "</p>");

    box.addEventListener("click", async function (e) {
      var t = e.target, v;
      if ((v = t.getAttribute("data-del-comment"))) {
        if (!confirm("Delete your comment?")) return;
        await asr.client.from("comments").delete().eq("id", v).eq("user_id", user.id); load();
      } else if ((v = t.getAttribute("data-hide-comment"))) {
        if (!confirm("Remove this comment from the site?")) return;
        await asr.client.from("comments").update({ status: "hidden" }).eq("id", v); load();
      }
    });

    var form = box.querySelector(".comment-form");
    if (form) form.addEventListener("submit", async function (e) {
      e.preventDefault();
      var body = form.querySelector("textarea").value.trim(), st = form.querySelector(".form-status");
      if (!body) return;
      var row = { user_id: user.id, body: body, status: "approved" };
      row[key] = id;
      var r = await asr.client.from("comments").insert(row);
      // Until supabase/comments-live.sql has been run, the database only accepts comments held for approval.
      if (r.error) { row.status = "pending"; r = await asr.client.from("comments").insert(row); }
      if (r.error) { st.innerHTML = '<p class="msg">Couldn’t post your comment: ' + esc(r.error.message) + "</p>"; return; }
      asr.log("commented", { on: key, id: id });
      form.reset();
      st.innerHTML = '<p class="msg">' + (row.status === "approved" ? "Thanks, your " + words.one + " is up." : "Thanks. Your " + words.one + " will appear once an organiser has read it.") + "</p>";
      load();
    });

    await load();
  }

  window.forum = { when: when, prose: prose, signInLink: signInLink, me: me, rpc: rpc, comments: comments };
})();
