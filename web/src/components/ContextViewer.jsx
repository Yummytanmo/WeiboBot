import React from 'react';
import {
    Box,
    Paper,
    Typography,
    Grid,
    Card,
    CardContent,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    List,
    ListItem,
    ListItemText,
    Divider
} from '@mui/material';
import {
    Schedule as ScheduleIcon,
    Article as ArticleIcon,
    Forum as ForumIcon,
    CheckCircle as CheckCircleIcon,
    Cancel as CancelIcon
} from '@mui/icons-material';

const ContextViewer = ({ contextData }) => {
    if (!contextData) {
        return (
            <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>No context data available</Typography>
            </Box>
        );
    }

    const { schedule, posts = [], interactions = [], metadata = {} } = contextData;

    // 统计数据
    const stats = [
        {
            label: 'Schedule Items',
            value: schedule?.items?.length || 0,
            icon: <ScheduleIcon />,
            color: 'primary'
        },
        {
            label: 'Posts',
            value: posts.length,
            icon: <ArticleIcon />,
            color: 'success'
        },
        {
            label: 'Interactions',
            value: interactions.length,
            icon: <ForumIcon />,
            color: 'info'
        }
    ];

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return 'error';
            case 'medium': return 'warning';
            case 'low': return 'success';
            default: return 'default';
        }
    };

    const getActionIcon = (action) => {
        return action === 'post' ? '✍️' : '👀';
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* 统计卡片 */}
            <Grid container spacing={2}>
                {stats.map((stat, idx) => (
                    <Grid item xs={4} key={idx}>
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                    <Box sx={{ color: `${stat.color}.main` }}>
                                        {stat.icon}
                                    </Box>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold">
                                            {stat.value}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {stat.label}
                                        </Typography>
                                    </Box>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Schedule */}
            {schedule && schedule.items && schedule.items.length > 0 && (
                <Paper sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <ScheduleIcon color="primary" />
                        <Typography variant="h6" fontWeight="bold">
                            📅 Schedule - {schedule.date}
                        </Typography>
                    </Box>
                    {schedule.summary && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {schedule.summary}
                        </Typography>
                    )}
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell><strong>Time</strong></TableCell>
                                    <TableCell><strong>Action</strong></TableCell>
                                    <TableCell><strong>Topic/Notes</strong></TableCell>
                                    <TableCell><strong>Priority</strong></TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {schedule.items.map((item, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell>{item.time}</TableCell>
                                        <TableCell>
                                            <Chip
                                                label={item.action}
                                                size="small"
                                                icon={<span>{getActionIcon(item.action)}</span>}
                                                color={item.action === 'post' ? 'primary' : 'default'}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            {item.topic && (
                                                <Typography variant="body2" fontWeight="bold">
                                                    {item.topic}
                                                </Typography>
                                            )}
                                            {item.notes && (
                                                <Typography variant="caption" color="text.secondary">
                                                    {item.notes}
                                                </Typography>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={item.priority || 'medium'}
                                                size="small"
                                                color={getPriorityColor(item.priority)}
                                            />
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Paper>
            )}

            {/* Posts */}
            {posts.length > 0 && (
                <Paper sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <ArticleIcon color="success" />
                        <Typography variant="h6" fontWeight="bold">
                            ✍️ Generated Posts ({posts.length})
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {posts.map((post, idx) => (
                            <Card key={idx} variant="outlined">
                                <CardContent>
                                    <Typography variant="subtitle2" color="primary" gutterBottom>
                                        📝 {post.topic || 'Post ' + (idx + 1)}
                                    </Typography>
                                    <Typography variant="body2" sx={{ my: 1, whiteSpace: 'pre-wrap' }}>
                                        {post.final || post.draft}
                                    </Typography>
                                    <Divider sx={{ my: 1 }} />
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                        {post.posted ? (
                                            <Chip
                                                icon={<CheckCircleIcon />}
                                                label="Posted"
                                                color="success"
                                                size="small"
                                            />
                                        ) : (
                                            <Chip
                                                icon={<CancelIcon />}
                                                label="Draft Only"
                                                color="default"
                                                size="small"
                                            />
                                        )}
                                        {post.weibo_id && (
                                            <Chip
                                                label={`ID: ${post.weibo_id}`}
                                                size="small"
                                                variant="outlined"
                                            />
                                        )}
                                        {post.review?.approved && (
                                            <Chip
                                                label="Review: Approved"
                                                color="success"
                                                size="small"
                                                variant="outlined"
                                            />
                                        )}
                                    </Box>
                                </CardContent>
                            </Card>
                        ))}
                    </Box>
                </Paper>
            )}

            {/* Interactions */}
            {interactions.length > 0 && (
                <Paper sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <ForumIcon color="info" />
                        <Typography variant="h6" fontWeight="bold">
                            💬 Interactions ({interactions.length})
                        </Typography>
                    </Box>
                    <List>
                        {interactions.map((interaction, idx) => {
                            const decision = interaction.decision || {};
                            const actionIcon = {
                                'like': '👍',
                                'comment': '💬',
                                'repost': '🔄',
                                'skip': '⏭️'
                            }[decision.action_type] || '❓';

                            return (
                                <React.Fragment key={idx}>
                                    <ListItem>
                                        <ListItemText
                                            primary={
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <span>{actionIcon}</span>
                                                    <Chip
                                                        label={decision.action_type}
                                                        size="small"
                                                        color="primary"
                                                    />
                                                    <Typography variant="caption" color="text.secondary">
                                                        → {decision.target_object}
                                                    </Typography>
                                                </Box>
                                            }
                                            secondary={
                                                <Box sx={{ mt: 0.5 }}>
                                                    {decision.action_content && (
                                                        <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                                                            "{decision.action_content}"
                                                        </Typography>
                                                    )}
                                                    {decision.reason && (
                                                        <Typography variant="caption" color="text.secondary">
                                                            Reason: {decision.reason}
                                                        </Typography>
                                                    )}
                                                </Box>
                                            }
                                        />
                                    </ListItem>
                                    {idx < interactions.length - 1 && <Divider />}
                                </React.Fragment>
                            );
                        })}
                    </List>
                </Paper>
            )}

            {/* Metadata */}
            {Object.keys(metadata).length > 0 && (
                <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Metadata
                    </Typography>
                    <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
                        <Typography variant="caption" fontFamily="monospace" component="pre">
                            {JSON.stringify(metadata, null, 2)}
                        </Typography>
                    </Box>
                </Paper>
            )}
        </Box>
    );
};

export default ContextViewer;
