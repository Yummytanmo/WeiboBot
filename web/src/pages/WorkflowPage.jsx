import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Box,
    Grid,
    Paper,
    Typography,
    List,
    ListItem,
    ListItemText,
    ListItemButton,
    Chip,
    IconButton,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    Divider,
    Tabs,
    Tab
} from '@mui/material';
import {
    Add as AddIcon,
    Refresh as RefreshIcon,
    CheckCircle as CheckCircleIcon,
    Error as ErrorIcon,
    Schedule as ScheduleIcon,
    PlayArrow as PlayArrowIcon
} from '@mui/icons-material';
import ContextViewer from '../components/ContextViewer';
import WorkflowChainDisplay from '../components/WorkflowChainDisplay';

const API_BASE = 'http://localhost:8000/api/workflow';

const WorkflowPage = () => {
    const [runs, setRuns] = useState([]);
    const [selectedRun, setSelectedRun] = useState(null);
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(false);
    const [triggerModalOpen, setTriggerModalOpen] = useState(false);
    const [activeTab, setActiveTab] = useState(0); // 0=Details, 1=Context

    const [formData, setFormData] = useState({
        workflow: 'browse',
        agent_id: '',
        model: '',
    });

    useEffect(() => {
        fetchRuns();
        fetchConfig();
        const interval = setInterval(fetchRuns, 5000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (selectedRun && selectedRun.status === 'running') {
            const interval = setInterval(() => fetchRunDetails(selectedRun.id), 2000);
            return () => clearInterval(interval);
        }
    }, [selectedRun]);

    const fetchRuns = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/workflows`);
            setRuns(res.data.runs);
        } catch (err) {
            console.error('Failed to fetch runs', err);
        }
    };

    const fetchConfig = async () => {
        try {
            const res = await axios.get(`${API_BASE}/api/workflows/config`);
            setConfig(res.data);
            if (res.data.accounts.length > 0) {
                setFormData(prev => ({ ...prev, agent_id: res.data.accounts[0].account_id }));
            }
        } catch (err) {
            console.error('Failed to fetch config', err);
        }
    };

    const fetchRunDetails = async (runId) => {
        try {
            const res = await axios.get(`${API_BASE}/api/workflows/run/${runId}`);
            setSelectedRun(res.data);
        } catch (err) {
            console.error('Failed to fetch run details', err);
        }
    };

    const triggerWorkflow = async () => {
        if (!formData.agent_id) {
            alert('Please select an Agent Account.');
            return;
        }

        try {
            setLoading(true);
            const payload = { ...formData };
            // Ensure agent_id is a string
            if (payload.agent_id) {
                payload.agent_id = String(payload.agent_id);
            }

            Object.keys(payload).forEach(key => {
                if (payload[key] === '' || payload[key] === null) delete payload[key];
            });

            const res = await axios.post(`${API_BASE}/api/workflows/run`, payload);
            setTriggerModalOpen(false);
            fetchRuns();
            fetchRunDetails(res.data.run_id);
        } catch (err) {
            console.error('Failed to trigger workflow', err);
            let errorMessage = err.message;
            if (err.response?.data?.detail) {
                if (Array.isArray(err.response.data.detail)) {
                    errorMessage = err.response.data.detail
                        .map(e => `${e.loc.join('.')}: ${e.msg}`)
                        .join('\n');
                } else {
                    errorMessage = err.response.data.detail;
                }
            }
            alert('Failed to trigger workflow:\n' + errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const getStatusChip = (status) => {
        switch (status) {
            case 'success': return <Chip icon={<CheckCircleIcon />} label="Success" color="success" size="small" />;
            case 'error': return <Chip icon={<ErrorIcon />} label="Error" color="error" size="small" />;
            case 'running': return <Chip icon={<CircularProgress size={16} />} label="Running" color="primary" size="small" />;
            default: return <Chip icon={<ScheduleIcon />} label={status} size="small" />;
        }
    };

    return (
        <Box sx={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
            {/* Sidebar List */}
            <Paper sx={{ width: 300, display: 'flex', flexDirection: 'column', borderRadius: 0, borderRight: 1, borderColor: 'divider' }}>
                <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
                    <Typography variant="subtitle1" fontWeight="bold">Recent Runs</Typography>
                    <IconButton color="primary" onClick={() => setTriggerModalOpen(true)}>
                        <AddIcon />
                    </IconButton>
                </Box>
                <List sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    {runs.map(run => (
                        <ListItem key={run.id} disablePadding>
                            <ListItemButton
                                selected={selectedRun?.id === run.id}
                                onClick={() => fetchRunDetails(run.id)}
                                sx={{ flexDirection: 'column', alignItems: 'flex-start', gap: 1 }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                    <Typography variant="body2" fontWeight="bold">{run.workflow}</Typography>
                                    {getStatusChip(run.status)}
                                </Box>
                                <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                                    {run.id.slice(0, 8)}...
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                    {new Date(run.created_at).toLocaleString()}
                                </Typography>
                            </ListItemButton>
                        </ListItem>
                    ))}
                </List>
            </Paper>

            {/* Main Details Area */}
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', p: 3 }}>
                {selectedRun ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 3 }}>
                        <Paper sx={{ p: 3 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                                {getStatusChip(selectedRun.status)}
                                <Typography variant="h5" fontWeight="bold">{selectedRun.workflow}</Typography>
                                <Chip label={selectedRun.id} variant="outlined" size="small" sx={{ fontFamily: 'monosp ace' }} />
                            </Box>

                            {/* Workflow Chain */}
                            {selectedRun.workflow_chain && (
                                <WorkflowChainDisplay workflowChain={selectedRun.workflow_chain} />
                            )}

                            {selectedRun.status === 'running' && selectedRun.current_step && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, bgcolor: 'primary.dark', p: 2, borderRadius: 1, color: 'primary.contrastText' }}>
                                    <CircularProgress size={20} color="inherit" />
                                    <Typography variant="body1" fontWeight="bold">
                                        {selectedRun.current_step}...
                                    </Typography>
                                </Box>
                            )}
                            <Grid container spacing={2}>
                                <Grid item xs={4}>
                                    <Typography variant="caption" color="text.secondary">Created</Typography>
                                    <Typography variant="body2">{new Date(selectedRun.created_at).toLocaleString()}</Typography>
                                </Grid>
                                <Grid item xs={4}>
                                    <Typography variant="caption" color="text.secondary">Started</Typography>
                                    <Typography variant="body2">{selectedRun.started_at ? new Date(selectedRun.started_at).toLocaleString() : '-'}</Typography>
                                </Grid>
                                <Grid item xs={4}>
                                    <Typography variant="caption" color="text.secondary">Finished</Typography>
                                    <Typography variant="body2">{selectedRun.finished_at ? new Date(selectedRun.finished_at).toLocaleString() : '-'}</Typography>
                                </Grid>
                            </Grid>
                        </Paper>

                        {/* Tabs */}
                        <Paper>
                            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
                                <Tab label="Details & Logs" />
                                <Tab label="Context Data" disabled={!selectedRun.context_data} />
                            </Tabs>
                        </Paper>

                        {activeTab === 0 && (
                            <Box sx={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <Paper sx={{ p: 2 }}>
                                    <Typography variant="subtitle2" gutterBottom>Parameters</Typography>
                                    <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1, overflowX: 'auto' }}>
                                        <Typography variant="caption" fontFamily="monospace" component="pre">
                                            {JSON.stringify(selectedRun.params, null, 2)}
                                        </Typography>
                                    </Box>
                                </Paper>

                                {selectedRun.error && (
                                    <Paper sx={{ p: 2, bgcolor: 'error.dark', color: 'error.contrastText' }}>
                                        <Typography variant="subtitle2" gutterBottom>Error</Typography>
                                        <Typography variant="body2" fontFamily="monospace" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                                            {selectedRun.error}
                                        </Typography>
                                    </Paper>
                                )}

                                {selectedRun.result && (
                                    <Paper sx={{ p: 2, bgcolor: 'success.dark', color: 'success.contrastText' }}>
                                        <Typography variant="subtitle2" gutterBottom>Result</Typography>
                                        <Typography variant="body2" fontFamily="monospace" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                                            {typeof selectedRun.result === 'string' ? selectedRun.result : JSON.stringify(selectedRun.result, null, 2)}
                                        </Typography>
                                    </Paper>
                                )}

                                <Paper sx={{ p: 2, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                                    <Typography variant="subtitle2" gutterBottom>Logs</Typography>
                                    <Box sx={{ bgcolor: 'black', color: 'grey.300', p: 2, borderRadius: 1, flexGrow: 1, overflowY: 'auto', minHeight: 200 }}>
                                        <Typography variant="caption" fontFamily="monospace" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                                            {selectedRun.logs || 'No logs available.'}
                                        </Typography>
                                    </Box>
                                </Paper>
                            </Box>
                        )}

                        {activeTab === 1 && selectedRun.context_data && (
                            <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                                <ContextViewer contextData={selectedRun.context_data} />
                            </Box>
                        )}
                    </Box>
                ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'text.secondary' }}>
                        <PlayArrowIcon sx={{ fontSize: 60, opacity: 0.2, mb: 2 }} />
                        <Typography variant="h6">Select a run to view details</Typography>
                    </Box>
                )
                }
            </Box >

            {/* Trigger Modal */}
            < Dialog open={triggerModalOpen} onClose={() => setTriggerModalOpen(false)} maxWidth="sm" fullWidth >
                <DialogTitle>Start New Workflow</DialogTitle>
                <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
                        <FormControl fullWidth>
                            <InputLabel>Workflow Type</InputLabel>
                            <Select
                                value={formData.workflow}
                                label="Workflow Type"
                                onChange={(e) => setFormData({ ...formData, workflow: e.target.value })}
                            >
                                <MenuItem value="browse">Browse Interaction</MenuItem>
                                <MenuItem value="post_review">Post Review</MenuItem>
                                <MenuItem value="daily">Daily Agent</MenuItem>
                                <Divider />
                                <MenuItem value="schedule_post">🔗 Schedule → Post</MenuItem>
                                <MenuItem value="schedule_browse">🔗 Schedule → Browse</MenuItem>
                                <MenuItem value="full_chain">🔗 Full Chain (Schedule → Post → Browse)</MenuItem>
                            </Select>
                        </FormControl>

                        <FormControl fullWidth>
                            <InputLabel>Agent Account</InputLabel>
                            <Select
                                value={formData.agent_id}
                                label="Agent Account"
                                onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                            >
                                {config?.accounts?.map(acc => (
                                    <MenuItem key={acc.account_id} value={acc.account_id}>{acc.account_id}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        {formData.workflow === 'post_review' && (
                            <>
                                <TextField
                                    label="Topic"
                                    fullWidth
                                    value={formData.topic || ''}
                                    onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                                />
                                <TextField
                                    label="Notes"
                                    fullWidth
                                    multiline
                                    rows={3}
                                    value={formData.notes || ''}
                                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                />
                            </>
                        )}

                        {(formData.workflow === 'browse' || formData.workflow === 'daily') && (
                            <Box sx={{ display: 'flex', gap: 2 }}>
                                <TextField
                                    label="Following Count"
                                    type="number"
                                    fullWidth
                                    value={formData.n_following || ''}
                                    onChange={(e) => setFormData({ ...formData, n_following: parseInt(e.target.value) || '' })}
                                />
                                <TextField
                                    label="Recommend Count"
                                    type="number"
                                    fullWidth
                                    value={formData.n_recommend || ''}
                                    onChange={(e) => setFormData({ ...formData, n_recommend: parseInt(e.target.value) || '' })}
                                />
                            </Box>
                        )}

                        {formData.workflow === 'daily' && (
                            <>
                                <Typography variant="subtitle2" color="primary" sx={{ mt: 1 }}>
                                    ⏰ Time Scheduling Options
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                    <TextField
                                        label="Check Interval (seconds)"
                                        type="number"
                                        fullWidth
                                        placeholder="60"
                                        value={formData.check_interval || ''}
                                        onChange={(e) => setFormData({ ...formData, check_interval: parseInt(e.target.value) || '' })}
                                        helperText="How often to check for tasks"
                                    />
                                    <TextField
                                        label="Time Tolerance (minutes)"
                                        type="number"
                                        fullWidth
                                        placeholder="5"
                                        value={formData.tolerance_minutes || ''}
                                        onChange={(e) => setFormData({ ...formData, tolerance_minutes: parseInt(e.target.value) || '' })}
                                        helperText="Time window for execution"
                                    />
                                </Box>
                                <FormControl component="fieldset">
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_once || false}
                                            onChange={(e) => setFormData({ ...formData, run_once: e.target.checked })}
                                        />
                                        <Typography variant="body2">
                                            Run Once (execute only current time tasks and exit)
                                        </Typography>
                                    </Box>
                                </FormControl>
                            </>
                        )}
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setTriggerModalOpen(false)}>Cancel</Button>
                    <Button
                        onClick={triggerWorkflow}
                        variant="contained"
                        disabled={loading}
                        startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                    >
                        Start
                    </Button>
                </DialogActions>
            </Dialog >
        </Box >
    );
};

export default WorkflowPage;
