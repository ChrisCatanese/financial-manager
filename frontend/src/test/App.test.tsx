import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders the header', () => {
    render(<App />);
    expect(screen.getByText('Financial Manager')).toBeInTheDocument();
  });

  it('renders navigation buttons', () => {
    render(<App />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Calculator')).toBeInTheDocument();
  });

  it('renders the pipeline dashboard by default', () => {
    render(<App />);
    expect(screen.getByText('Pipeline Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Run Full Pipeline')).toBeInTheDocument();
  });

  it('navigates to calculator view', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Calculator'));
    expect(screen.getByLabelText('Gross Income')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /calculate tax/i })).toBeInTheDocument();
  });

  it('navigates to documents view', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Documents'));
    expect(screen.getByText(/No Checklist Yet/)).toBeInTheDocument();
  });
});
