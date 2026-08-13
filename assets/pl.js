/* PUPLESS 計測タグ ローダー
   ------------------------------------------------------------------
   本番ドメイン(getpupless.com)でのみ実IDのタグを読み込む。
   localhost や Cloudflare のプレビュー(*.pages.dev)では外部へ一切送信せず、
   window.PUPLESS_EVENTS に積んで console に出すだけ（テストモード）。

   使い方:  pupless.track('cta_click', { cta: 'hero' });
   確認  :  console で PUPLESS_EVENTS を見る / pupless.mode でモード確認
   ------------------------------------------------------------------ */
(function () {
  'use strict';

  /* ---- 1. 計測ID：発行されたらここを埋めるだけ（空文字の間は読み込まない） ---- */
  var IDS = {
    ga4:     'G-3SR19RT9LQ',   /* 'G-XXXXXXXXXX'   Google アナリティクス4 */
    ads:     '',   /* 'AW-XXXXXXXXX'   Google 広告（コンバージョン計測用） */
    meta:    '901097342555400',   /* '1234567890123'  Meta ピクセル */
    clarity: 'y1nxqpcfc8'    /* 'abcdefghij'     Microsoft Clarity */
  };

  /* ---- 2. 本番として扱うホスト。ここに無ければ全てテストモード ---- */
  var PROD_HOSTS = ['getpupless.com', 'www.getpupless.com'];

  /* ---- 3. Meta の標準イベント名への対応表（無いものは trackCustom で送る） ----
     Lead に何を割り当てるかは配信の最適化先そのものになる。今の成果は
     「入荷通知の申込み」なので restock_email_submit を Lead にしている。
     cta_click を Lead にすると「押すだけで離脱する人」を増やす方向に
     最適化されてしまうため、標準イベントには割り当てない（custom で送る）。
     販売開始で購入導線が繋がったら Purchase を最上位に据え直すこと。 */
  var META_STANDARD = {
    restock_email_submit: 'Lead',
    begin_checkout:       'InitiateCheckout',
    purchase:             'Purchase'
  };

  var isProd = PROD_HOSTS.indexOf(location.hostname) !== -1;
  /* 本番でも ?pupless_debug=1 を付ければ console に出る（送信はそのまま行う） */
  var verbose = !isProd || location.search.indexOf('pupless_debug=1') !== -1;

  /* ---- 内部トラフィック（自社の動作確認）の目印 ---------------------
     固定IPが無くても除外できるよう、?pupless_internal=1 を付けて開いた
     ブラウザを内部として記憶し、GA4 に traffic_type=internal を付けて送る。
     GA4 側は「データフィルタ → 内部トラフィック」を有効にするだけでよい。
     解除は ?pupless_internal=0 。今の状態は pupless.internal で確認できる。 */
  var isInternal = (function () {
    var m = location.search.match(/[?&]pupless_internal=([01])/);
    try {
      if (m) {
        if (m[1] === '1') localStorage.setItem('pupless_internal', '1');
        else              localStorage.removeItem('pupless_internal');
      }
      return localStorage.getItem('pupless_internal') === '1';
    } catch (e) {
      /* localStorage が使えない場合はそのページ限りの判定にする */
      return !!(m && m[1] === '1');
    }
  })();

  var events = [];

  function log(name, params) {
    var record = { name: name, params: params || {}, at: new Date().toISOString() };
    events.push(record);
    if (verbose) console.info('[PUPLESS/' + (isProd ? 'prod' : 'test') +
                              (isInternal ? '/internal' : '') + '] ' + name, record.params);
  }

  /* ---- 4. 本番タグの読み込み ------------------------------------- */
  function loadScript(src) {
    var s = document.createElement('script');
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
  }

  function loadGoogle() {
    if (!IDS.ga4 && !IDS.ads) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    gtag('js', new Date());
    loadScript('https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(IDS.ga4 || IDS.ads));
    /* traffic_type は config で渡すと、そのページの全イベントに付く */
    var cfg = isInternal ? { traffic_type: 'internal' } : {};
    if (IDS.ga4) gtag('config', IDS.ga4, cfg);
    if (IDS.ads) gtag('config', IDS.ads, cfg);
  }

  function loadMeta() {
    if (!IDS.meta) return;
    /* Meta 公式スニペット（fbq のスタブを先に作り、本体を後から読み込む） */
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v;
      s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', IDS.meta);
    fbq('track', 'PageView');
  }

  function loadClarity() {
    if (!IDS.clarity) return;
    window.clarity = window.clarity || function () { (window.clarity.q = window.clarity.q || []).push(arguments); };
    loadScript('https://www.clarity.ms/tag/' + encodeURIComponent(IDS.clarity));
    /* Clarity にはGA4のような内部トラフィック除外が無いため、カスタムタグを付けて
       ダッシュボードのフィルタ（traffic_type = internal）で外せるようにする。 */
    if (isInternal) clarity('set', 'traffic_type', 'internal');
  }

  if (isProd) {
    loadGoogle();
    loadMeta();
    loadClarity();
  }

  /* ---- 5. 送信の入口。ページ側はこれだけ呼べばよい ---------------- */
  function track(name, params) {
    params = params || {};
    log(name, params);
    if (!isProd) return;   /* テストモードでは外部に出さない */

    if (typeof gtag === 'function') gtag('event', name, params);

    if (typeof fbq === 'function') {
      var std = META_STANDARD[name];
      if (std) fbq('track', std, params);
      else     fbq('trackCustom', name, params);
    }

    if (typeof clarity === 'function') {
      clarity('event', name);
      /* Clarity は数値/文字列のタグのみ受けるので、値は文字列化して渡す */
      Object.keys(params).forEach(function (k) {
        clarity('set', k, String(params[k]));
      });
    }
  }

  /* 同一セッション内で1回だけ送る。モーダルの開き直しや連打でイベント数が
     水増しされると困るもの（キーイベント候補）に使う。
     key を省くとイベント名だけで判定。'名前:値' を渡せば値ごとに1回になる。
     テストで再送したいときは sessionStorage.clear() か新しいタブで開く。 */
  var onceMemo = {};

  function trackOnce(name, params, key) {
    var k = 'pupless_once:' + (key || name);
    if (onceMemo[k]) { if (verbose) console.info('[PUPLESS] ' + name + ' は送信済みのため抑制', k); return false; }
    try {
      if (sessionStorage.getItem(k)) {
        onceMemo[k] = 1;
        if (verbose) console.info('[PUPLESS] ' + name + ' は送信済みのため抑制', k);
        return false;
      }
      sessionStorage.setItem(k, '1');
    } catch (e) { /* プライベートモード等で使えない場合はメモリだけで判定する */ }
    onceMemo[k] = 1;
    track(name, params);
    return true;
  }

  /* Google 広告のコンバージョン（send_to は 'AW-XXXX/ラベル' 形式） */
  function conversion(sendTo, params) {
    log('conversion', { send_to: sendTo });
    if (!isProd || typeof gtag !== 'function' || !sendTo) return;
    var payload = { send_to: sendTo };
    Object.keys(params || {}).forEach(function (k) { payload[k] = params[k]; });
    gtag('event', 'conversion', payload);
  }

  window.pupless = {
    mode: isProd ? 'production' : 'test',
    internal: isInternal,
    ids: IDS,
    events: events,
    track: track,
    trackOnce: trackOnce,
    conversion: conversion
  };
  window.PUPLESS_EVENTS = events;   /* console から確認しやすいように別名も置く */

  /* ページビューは GA4 の config と Meta の init が自動で送るので、
     ここでは記録だけ（テストモードでも1件目として見えるようにする）。 */
  log('page_view', { page: location.pathname });
})();
