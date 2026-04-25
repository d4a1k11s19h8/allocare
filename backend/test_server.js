const express = require('express');
const path = require('path');
const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    data: { needs: 10, volunteers: 5 },
    gemini_api_key_configured: true
  });
});

app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body;
  if (email === 'superadmin@allocare.org') {
    res.json({
      message: 'Login successful',
      user: {
        id: 'u3',
        email: 'superadmin@allocare.org',
        display_name: 'Super Admin',
        role: 'superadmin'
      }
    });
  } else {
    res.status(401).json({ detail: 'Invalid credentials' });
  }
});

app.get('/api/needs', (req, res) => {
  res.json({ needs: [] });
});

app.get('/api/system/keys/health', (req, res) => {
  res.json({
    status: 'success',
    keys: {
      summary: {
        total_keys: 3,
        healthy_keys: 2,
        rate_limited_keys: 0,
        retired_keys: 1
      },
      keys: {
        'key1': {
          status: 'active',
          key_suffix: '123A',
          rpm_used: 5,
          rpd_used: 100,
          failure_count: 0,
          cooldown_remaining_s: 0
        },
        'key2': {
          status: 'active',
          key_suffix: '456B',
          rpm_used: 2,
          rpd_used: 50,
          failure_count: 0,
          cooldown_remaining_s: 0
        },
        'key3': {
          status: 'retired',
          key_suffix: '789C',
          rpm_used: 0,
          rpd_used: 0,
          failure_count: 5,
          cooldown_remaining_s: 0
        }
      }
    }
  });
});

app.listen(8001, () => console.log('Mock server running on port 8001'));
