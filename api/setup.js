// api/setup.js — регистрация webhook в Telegram
// Открой в браузере: https://your-project.vercel.app/api/setup
// Достаточно сделать один раз после деплоя

const BOT_TOKEN = process.env.BOT_TOKEN;

module.exports = async function handler(req, res) {
    const host = req.headers.host;
    const webhookUrl = `https://${host}/api/webhook`;

    try {
        // Регистрируем webhook
        const setRes = await fetch(
            `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: webhookUrl,
                    allowed_updates: ['message', 'callback_query']
                })
            }
        );
        const setData = await setRes.json();

        // Проверяем текущий статус
        const infoRes = await fetch(
            `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo`
        );
        const infoData = await infoRes.json();

        // Отвечаем красивой HTML страницей
        const html = `
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bot Setup</title>
<style>
    body { font-family: Arial, sans-serif; background: #17212b; color: white; padding: 30px; max-width: 600px; margin: 0 auto; }
    h2 { color: #6ab2f2; }
    .ok { color: #89ED5E; }
    .err { color: #ff6b6b; }
    pre { background: #1d2b3a; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 13px; color: #6ab2f2; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
    .badge.ok { background: #1a3a1a; color: #89ED5E; }
    .badge.err { background: #3a1a1a; color: #ff6b6b; }
</style>
</head>
<body>
<h2>🤖 Bot Webhook Setup</h2>

<p>Webhook URL: <code>${webhookUrl}</code></p>

<p>Результат регистрации: 
    <span class="badge ${setData.ok ? 'ok' : 'err'}">
        ${setData.ok ? '✅ ' + setData.description : '❌ ' + (setData.description || 'Ошибка')}
    </span>
</p>

<h3>Текущий статус webhook:</h3>
<pre>${JSON.stringify(infoData.result, null, 2)}</pre>

${setData.ok ? '<p class="ok">✅ Бот готов к работе! Напиши /order в Telegram.</p>' : '<p class="err">❌ Проверь BOT_TOKEN в переменных окружения Vercel.</p>'}
</body>
</html>`;

        return res.status(200).send(html);
    } catch (err) {
        return res.status(500).send(`<pre style="color:red">Error: ${err.message}</pre>`);
    }
}
