import React from 'react';
import { Handle, Position } from 'reactflow';
import { Box, Typography, Paper } from '@mui/material';

const CustomNode = ({ data, selected }) => {
    return (
        <Paper
            elevation={selected ? 8 : 2}
            sx={{
                padding: 2,
                border: 2,
                borderColor: selected ? 'primary.main' : 'transparent',
                minWidth: 180,
                bgcolor: 'background.paper',
            }}
        >
            <Handle type="target" position={Position.Top} style={{ background: '#555' }} />

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <span style={{ fontSize: '1.5em' }}>{data.icon}</span>
                <Typography variant="subtitle2" fontWeight="bold">
                    {data.label}
                </Typography>
            </Box>

            {data.description && (
                <Typography variant="caption" color="text.secondary" display="block">
                    {data.description}
                </Typography>
            )}

            <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
        </Paper>
    );
};

export default CustomNode;
