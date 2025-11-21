import React from 'react';
import { Box, Chip, Typography } from '@mui/material';
import { ArrowForward as ArrowIcon } from '@mui/icons-material';

const WorkflowChainDisplay = ({ workflowChain }) => {
    if (!workflowChain || workflowChain.length === 0) {
        return null;
    }

    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                Workflow Chain:
            </Typography>
            {workflowChain.map((workflow, idx) => (
                <React.Fragment key={idx}>
                    <Chip
                        label={workflow}
                        color="primary"
                        variant="outlined"
                        size="small"
                    />
                    {idx < workflowChain.length - 1 && (
                        <ArrowIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                    )}
                </React.Fragment>
            ))}
        </Box>
    );
};

export default WorkflowChainDisplay;
