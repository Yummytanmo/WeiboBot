import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
    Box,
    Paper,
    Typography,
    List,
    ListItem,
    ListItemButton,
    ListItemText,
    Chip,
    Button,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    IconButton,
    Stack,
    Divider,
} from '@mui/material';
import { Add as AddIcon, Refresh as RefreshIcon, Delete as DeleteIcon } from '@mui/icons-material';

const API_BASE = 'http://localhost:8000/api/workflow';

const WorkflowPage = () => {
    const [runs, setRuns] = useState([]);
    const [selectedRun, setSelectedRun] = useState(null);
    const [loading, setLoading] = useState(false);

    const [formData, setFormData] = useState({
        workflow: 'daily_schedule',
        agent_id: '7828522614',
        llm_model: 'gpt-4o-mini',
        current_post_topic: '',
        max_review_rounds: 2,
        min_slots: 3,
        max_slots: 5,
    });

    useEffect(() => {
        fetchRuns();
        const interval = setInterval(fetchRuns, 3000);
        return () => clearInterval(interval);
    }, []);

    // 自动刷新运行中的记录
    useEffect(() => {
        if (selectedRun?.status === 'running') {
            const interval = setInterval(() => fetchRunDetails(selectedRun.id), 2000);
            return () => clearInterval(interval);
        }
    }, [selectedRun]);

    const stats = useMemo(() => {
        const base = { running: 0, completed: 0, failed: 0 };
        runs.forEach((r) => {
            if (base[r.status] !== undefined) base[r.status] += 1;
        });
        return base;
    }, [runs]);

    const fetchRuns = async () => {
        try {
            const res = await axios.get(`${API_BASE}/runs`);
            setRuns(res.data.runs || []);
        } catch (err) {
            console.error('Failed to fetch runs', err);
        }
    };

    const fetchRunDetails = async (runId) => {
        try {
            const res = await axios.get(`${API_BASE}/run/${runId}`);
            setSelectedRun(res.data);
            setRuns((prev) =>
                prev.map((run) => (run.id === runId ? { ...run, status: res.data.status } : run))
            );
        } catch (err) {
            console.error('Failed to fetch run details', err);
        }
    };

    const triggerWorkflow = async () => {
        setLoading(true);
        try {
            const res = await axios.post(`${API_BASE}/trigger`, formData);
            fetchRuns();
            setTimeout(() => fetchRunDetails(res.data.run_id), 400);
        } catch (err) {
            console.error('Failed to trigger workflow', err);
            alert('Failed to trigger workflow: ' + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const deleteRun = async (runId) => {
        try {
            await axios.delete(`${API_BASE}/run/${runId}`);
            setRuns((prev) => prev.filter((run) => run.id !== runId));
            if (selectedRun?.id === runId) {
                setSelectedRun(null);
            }
        } catch (err) {
            console.error('Failed to delete run', err);
        }
    };

    const getStatusColor = (status) => {
        const colors = {
            pending: 'default',
            running: 'primary',
            completed: 'success',
            failed: 'error',
        };
        return colors[status] || 'default';
    };

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>Workflow Orchestrator</Typography>
                    <Typography variant="body2" color="text.secondary">n8n 风格：左侧运行列表，中间画布，右侧检查面板</Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={fetchRuns}
                        size="small"
                    >
                        Refresh
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={triggerWorkflow}
                        disabled={loading || !formData.agent_id}
                        size="small"
                    >
                        {loading ? <CircularProgress size={18} /> : 'Run'}
                    </Button>
                </Box>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '300px 1fr 360px' }, gap: 2, height: '100%' }}>
                {/* 左侧：触发 + 运行列表 */}
                <Stack spacing={2} sx={{ height: '100%' }}>
                    <Paper sx={{ p: 2, boxShadow: 6, borderRadius: 2, bgcolor: 'background.paper' }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Quick Trigger</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            参考 n8n 左侧面板，直接配置参数并启动。
                        </Typography>
                        <Stack spacing={2}>
                            <FormControl fullWidth>
                                <InputLabel>Workflow</InputLabel>
                                <Select
                                    value={formData.workflow}
                                    label="Workflow"
                                    onChange={(e) => setFormData({ ...formData, workflow: e.target.value })}
                                >
                                    <MenuItem value="daily_schedule">Daily Schedule</MenuItem>
                                    <MenuItem value="post_review">Post Review</MenuItem>
                                    <MenuItem value="browse_interaction">Browse Interaction</MenuItem>
                                    <MenuItem value="daily_agent">Daily Agent (Full)</MenuItem>
                                </Select>
                            </FormControl>
                            <FormControl fullWidth>
                                <InputLabel>Agent ID</InputLabel>
                                <Select
                                    value={formData.agent_id}
                                    label="Agent ID"
                                    onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                                >
                                    <MenuItem value="7828522614">7828522614</MenuItem>
                                </Select>
                            </FormControl>
                            {(formData.workflow === 'post_review' || formData.workflow === 'daily_agent') && (
                                <TextField
                                    label="Post Topic"
                                    value={formData.current_post_topic}
                                    onChange={(e) => setFormData({ ...formData, current_post_topic: e.target.value })}
                                    placeholder="e.g., AI技术进展"
                                />
                            )}
                        </Stack>
                    </Paper>

                    <Paper sx={{ flex: 1, p: 2, overflow: 'auto', boxShadow: 6, borderRadius: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Runs</Typography>
                            <Stack direction="row" spacing={1}>
                                <Chip label={`Running ${stats.running}`} color="primary" size="small" />
                                <Chip label={`Done ${stats.completed}`} color="success" size="small" />
                                <Chip label={`Failed ${stats.failed}`} color="error" size="small" />
                            </Stack>
                        </Box>
                        <Divider sx={{ mb: 1 }} />
                        <List dense>
                            {runs.length === 0 && (
                                <ListItem>
                                    <ListItemText
                                        primary="No workflows yet"
                                        secondary="Click Run to start"
                                    />
                                </ListItem>
                            )}
                            {runs.map((run) => (
                                <ListItem
                                    key={run.id}
                                    disablePadding
                                    secondaryAction={
                                        <IconButton edge="end" onClick={() => deleteRun(run.id)} size="small">
                                            <DeleteIcon fontSize="small" />
                                        </IconButton>
                                    }
                                >
                                    <ListItemButton
                                        selected={selectedRun?.id === run.id}
                                        onClick={() => fetchRunDetails(run.id)}
                                        sx={{ borderRadius: 1, mb: 0.5 }}
                                    >
                                        <ListItemText
                                            primary={
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                                        {run.workflow.replace(/_/g, ' ')}
                                                    </Typography>
                                                    <Chip
                                                        label={run.status}
                                                        color={getStatusColor(run.status)}
                                                        size="small"
                                                    />
                                                </Box>
                                            }
                                            secondary={new Date(run.created_at).toLocaleString()}
                                        />
                                    </ListItemButton>
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Stack>

                {/* 中间：运行过程 */}
                <Paper sx={{ p: 2, boxShadow: 6, borderRadius: 2, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Run Progress</Typography>
                        {selectedRun && (
                            <Chip label={selectedRun.workflow.replace(/_/g, ' ')} color="secondary" size="small" />
                        )}
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        以列表方式展示节点执行顺序与状态（替代图形）。
                    </Typography>
                    {!selectedRun ? (
                        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'grey.900', borderRadius: 2 }}>
                            <Typography variant="body2" color="text.secondary">Select a run to view details</Typography>
                        </Box>
                    ) : (
                        <Box sx={{ flex: 1, minHeight: 360, borderRadius: 2, overflow: 'auto', bgcolor: 'grey.900', p: 1 }}>
                            {(selectedRun.nodes || []).length === 0 ? (
                                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                                    No node status reported yet.
                                </Typography>
                            ) : (
                                <List dense>
                                    {selectedRun.nodes.map((node) => (
                                        <ListItem key={node.id} sx={{ bgcolor: 'rgba(255,255,255,0.04)', borderRadius: 1, mb: 0.5 }}>
                                            <ListItemText
                                                primary={
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                                            {node.label || node.id}
                                                        </Typography>
                                                        <Chip
                                                            label={node.status}
                                                            color={getStatusColor(node.status)}
                                                            size="small"
                                                        />
                                                    </Box>
                                                }
                                                secondary={
                                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
                                                        {node.started_at && (
                                                            <Chip size="small" label={`Start: ${node.started_at}`} />
                                                        )}
                                                        {node.finished_at && (
                                                            <Chip size="small" label={`End: ${node.finished_at}`} />
                                                        )}
                                                        {node.duration && (
                                                            <Chip size="small" label={`Duration: ${node.duration.toFixed(2)}s`} />
                                                        )}
                                                        {node.error && (
                                                            <Chip size="small" color="error" label={`Error: ${node.error}`} />
                                                        )}
                                                    </Box>
                                                }
                                            />
                                        </ListItem>
                                    ))}
                                </List>
                            )}
                        </Box>
                    )}
                </Paper>

                    {/* 右侧：检查面板 */}
                <Paper sx={{ p: 2, boxShadow: 6, borderRadius: 2, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Inspector</Typography>
                    {!selectedRun ? (
                        <Typography variant="body2" color="text.secondary">Select a run to inspect details.</Typography>
                    ) : (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, height: '100%' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip label={selectedRun.status} color={getStatusColor(selectedRun.status)} size="small" />
                                {selectedRun.current_node && (
                                    <Chip label={`Current: ${selectedRun.current_node}`} size="small" color="warning" />
                                )}
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                                ID: {selectedRun.id}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Created: {new Date(selectedRun.created_at).toLocaleString()}
                            </Typography>
                            {selectedRun.started_at && (
                                <Typography variant="body2" color="text.secondary">
                                    Started: {new Date(selectedRun.started_at).toLocaleString()}
                                </Typography>
                            )}
                            {selectedRun.finished_at && (
                                <Typography variant="body2" color="text.secondary">
                                    Finished: {new Date(selectedRun.finished_at).toLocaleString()}
                                </Typography>
                            )}
                            <Divider sx={{ my: 1 }} />
                            <Typography variant="subtitle2">Params</Typography>
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, pr: 1 }}>
                                {selectedRun.params && Object.entries(selectedRun.params).map(([k, v]) => (
                                    <Box key={k} sx={{ bgcolor: 'grey.900', borderRadius: 1, p: 1 }}>
                                        <Typography variant="caption" color="text.secondary">{k}</Typography>
                                        <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                                            {v === null || v === undefined ? '-' : String(v)}
                                        </Typography>
                                    </Box>
                                ))}
                            </Box>
                            <Divider sx={{ my: 1 }} />
                            <Typography variant="subtitle2">Logs</Typography>
                            <Box sx={{ flex: 1, minHeight: 120, maxHeight: 200, overflow: 'auto', bgcolor: 'grey.900', borderRadius: 1, p: 1 }}>
                                <pre style={{ fontSize: '0.8em', margin: 0, whiteSpace: 'pre-wrap' }}>
                                    {selectedRun.logs || 'No logs yet...'}
                                </pre>
                            </Box>
                            {selectedRun.error && (
                                <Box sx={{ mt: 1, p: 1, bgcolor: 'error.light', borderRadius: 1 }}>
                                    <Typography variant="subtitle2" color="error.dark">Error</Typography>
                                    <Typography variant="body2" color="error.dark">{selectedRun.error}</Typography>
                                </Box>
                            )}
                        </Box>
                    )}
                </Paper>
            </Box>
        </Box>
    );
};

export default WorkflowPage;
