import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
    Box,
    Paper,
    Typography,
    TextField,
    Button,
    IconButton,
    Drawer,
    Slider,
    FormControlLabel,
    Switch,
    CircularProgress,
    Avatar,
    Stack
} from '@mui/material';
import {
    Send as SendIcon,
    Settings as SettingsIcon,
    Refresh as RefreshIcon,
    SmartToy as BotIcon,
    Person as PersonIcon,
    Bolt as BoltIcon
} from '@mui/icons-material';

const API_BASE = 'http://localhost:8000/api/agent';

const AgentPage = () => {
    const [config, setConfig] = useState(null);
    const [session, setSession] = useState(null);
    const [history, setHistory] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [streaming, setStreaming] = useState(true);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const messagesEndRef = useRef(null);

    const [sessionConfig, setSessionConfig] = useState({
        model: 'gpt-4o-mini',
        temperature: 0.2,
        streaming: true,
    });

    useEffect(() => {
        fetchConfig();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [history]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchConfig = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/config`);
            setConfig(res.data);
            setSessionConfig(prev => ({
                ...prev,
                ...res.data.defaults,
                streaming: true
            }));
        } catch (err) {
            console.error('Failed to fetch config', err);
        }
    };

    const createSession = async () => {
        try {
            setLoading(true);
            const res = await axios.post(`${API_BASE}/api/session`, sessionConfig);
            setSession(res.data);
            setHistory(res.data.history || []);
            setStreaming(res.data.streaming);
            setLoading(false);
        } catch (err) {
            console.error('Failed to create session', err);
            setLoading(false);
        }
    };

    const resetSession = async () => {
        if (!session) return;
        try {
            await axios.post(`${API_BASE}/api/session/reset`, { session_id: session.session_id });
            setHistory([]);
        } catch (err) {
            console.error('Failed to reset session', err);
        }
    };

    const sendMessage = async () => {
        if (!input.trim() || !session || loading) return;

        const userMsg = { role: 'user', content: input };
        setHistory(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        if (streaming) {
            try {
                const response = await fetch(`${API_BASE}/api/chat/stream`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: session.session_id, message: userMsg.content }),
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantMsg = { role: 'assistant', content: '', logs: [], status: 'thinking' };

                setHistory(prev => [...prev, assistantMsg]);

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const event = JSON.parse(line);
                            if (event.type === 'token') {
                                assistantMsg.content += event.payload.content;
                                setHistory(prev => {
                                    const newHistory = [...prev];
                                    newHistory[newHistory.length - 1] = { ...assistantMsg };
                                    return newHistory;
                                });
                            } else if (event.type === 'log') {
                                assistantMsg.logs.push(event.payload.content);
                                setHistory(prev => {
                                    const newHistory = [...prev];
                                    newHistory[newHistory.length - 1] = { ...assistantMsg };
                                    return newHistory;
                                });
                            } else if (event.type === 'status') {
                                assistantMsg.status = event.payload.state === 'executing'
                                    ? `Executing: ${event.payload.tool}...`
                                    : (event.payload.state === 'thinking' ? 'Thinking...' : null);

                                setHistory(prev => {
                                    const newHistory = [...prev];
                                    newHistory[newHistory.length - 1] = { ...assistantMsg };
                                    return newHistory;
                                });
                            } else if (event.type === 'final') {
                                assistantMsg.content = event.payload.output;
                                assistantMsg.status = null; // Clear status on finish
                                setHistory(prev => {
                                    const newHistory = [...prev];
                                    newHistory[newHistory.length - 1] = { ...assistantMsg };
                                    return newHistory;
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing stream', e);
                        }
                    }
                }
            } catch (err) {
                console.error('Stream error', err);
                setHistory(prev => [...prev, { role: 'system', content: 'Error: ' + err.message }]);
            } finally {
                setLoading(false);
            }
        } else {
            try {
                const res = await axios.post(`${API_BASE}/api/chat`, {
                    session_id: session.session_id,
                    message: userMsg.content
                });
                setHistory(res.data.history);
            } catch (err) {
                console.error('Chat error', err);
            } finally {
                setLoading(false);
            }
        }
    };

    return (
        <Box sx={{ display: 'flex', height: '100%', position: 'relative' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
                {!session ? (
                    <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3 }}>
                        <Avatar sx={{ width: 80, height: 80, bgcolor: 'primary.main' }}>
                            <BotIcon sx={{ fontSize: 40 }} />
                        </Avatar>
                        <Typography variant="h4" fontWeight="bold">Weibo Agent</Typography>
                        <Typography variant="body1" color="text.secondary">Initialize a session to start chatting.</Typography>
                        <Button
                            variant="contained"
                            size="large"
                            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <BoltIcon />}
                            onClick={createSession}
                            disabled={loading}
                        >
                            Start Session
                        </Button>
                    </Box>
                ) : (
                    <>
                        <Paper elevation={0} sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: 'success.main', boxShadow: '0 0 8px #66bb6a' }} />
                                <Typography variant="subtitle2" fontFamily="monospace">
                                    SESSION: {session.session_id.slice(0, 8)}
                                </Typography>
                            </Box>
                            <Box>
                                <IconButton onClick={resetSession} title="Reset Session">
                                    <RefreshIcon />
                                </IconButton>
                                <IconButton onClick={() => setSettingsOpen(true)} title="Settings">
                                    <SettingsIcon />
                                </IconButton>
                            </Box>
                        </Paper>

                        <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                            {history.map((msg, idx) => (
                                <Box
                                    key={idx}
                                    sx={{
                                        display: 'flex',
                                        gap: 2,
                                        flexDirection: msg.role === 'user' ? 'row-reverse' : 'column',
                                        maxWidth: msg.role === 'user' ? '80%' : '100%',
                                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start'
                                    }}
                                >
                                    {msg.role === 'user' ? (
                                        <>
                                            <Avatar sx={{ bgcolor: 'secondary.main' }}><PersonIcon /></Avatar>
                                            <Paper
                                                elevation={1}
                                                sx={{
                                                    p: 2,
                                                    borderRadius: 2,
                                                    bgcolor: 'secondary.dark',
                                                    color: 'secondary.contrastText'
                                                }}
                                            >
                                                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Typography>
                                            </Paper>
                                        </>
                                    ) : (
                                        <Box sx={{ display: 'flex', gap: 2 }}>
                                            <Avatar sx={{ bgcolor: 'primary.main' }}><BotIcon /></Avatar>
                                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, maxWidth: '80%' }}>
                                                {msg.logs && msg.logs.length > 0 && (
                                                    <Paper
                                                        elevation={0}
                                                        sx={{
                                                            p: 2,
                                                            bgcolor: 'background.default',
                                                            border: 1,
                                                            borderColor: 'divider',
                                                            borderRadius: 2,
                                                            fontFamily: 'monospace',
                                                            fontSize: '0.8rem',
                                                            color: 'text.secondary',
                                                            maxHeight: 300,
                                                            overflowY: 'auto'
                                                        }}
                                                    >
                                                        {msg.logs.map((log, i) => (
                                                            <div key={i}>{log}</div>
                                                        ))}
                                                    </Paper>
                                                )}

                                                {msg.status && (
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main', py: 1 }}>
                                                        <CircularProgress size={16} color="inherit" />
                                                        <Typography variant="caption" fontWeight="bold">{msg.status}</Typography>
                                                    </Box>
                                                )}

                                                {(msg.content || !msg.logs?.length) && (
                                                    <Paper
                                                        elevation={1}
                                                        sx={{
                                                            p: 2,
                                                            borderRadius: 2,
                                                            bgcolor: 'background.paper',
                                                            color: 'text.primary'
                                                        }}
                                                    >
                                                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Typography>
                                                    </Paper>
                                                )}
                                            </Box>
                                        </Box>
                                    )}
                                </Box>
                            ))}
                            <div ref={messagesEndRef} />
                        </Box>

                        <Paper elevation={3} sx={{ p: 2 }}>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <TextField
                                    fullWidth
                                    variant="outlined"
                                    placeholder="Type a message..."
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            sendMessage();
                                        }
                                    }}
                                    disabled={loading}
                                />
                                <IconButton
                                    color="primary"
                                    size="large"
                                    onClick={sendMessage}
                                    disabled={loading || !input.trim()}
                                    sx={{ bgcolor: 'primary.main', color: 'white', '&:hover': { bgcolor: 'primary.dark' } }}
                                >
                                    {loading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
                                </IconButton>
                            </Box>
                        </Paper>
                    </>
                )}
            </Box>

            <Drawer
                anchor="right"
                open={settingsOpen}
                onClose={() => setSettingsOpen(false)}
            >
                <Box sx={{ width: 300, p: 3 }}>
                    <Typography variant="h6" gutterBottom>Settings</Typography>
                    <Stack spacing={3} sx={{ mt: 2 }}>
                        <TextField
                            label="Model"
                            fullWidth
                            value={sessionConfig.model}
                            onChange={(e) => setSessionConfig({ ...sessionConfig, model: e.target.value })}
                        />
                        <Box>
                            <Typography gutterBottom>Temperature: {sessionConfig.temperature}</Typography>
                            <Slider
                                value={sessionConfig.temperature}
                                min={0}
                                max={2}
                                step={0.1}
                                onChange={(_, val) => setSessionConfig({ ...sessionConfig, temperature: val })}
                                valueLabelDisplay="auto"
                            />
                        </Box>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={sessionConfig.streaming}
                                    onChange={(e) => setSessionConfig({ ...sessionConfig, streaming: e.target.checked })}
                                />
                            }
                            label="Stream Responses"
                        />
                    </Stack>
                </Box>
            </Drawer>
        </Box>
    );
};

export default AgentPage;
