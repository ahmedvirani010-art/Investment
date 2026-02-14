import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../card';

describe('Card Components', () => {
  it('should render Card with children', () => {
    render(
      <Card>
        <div>Card content</div>
      </Card>
    );
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('should render CardHeader with title and description', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card Description</CardDescription>
        </CardHeader>
      </Card>
    );
    
    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card Description')).toBeInTheDocument();
  });

  it('should render CardContent', () => {
    render(
      <Card>
        <CardContent>
          <p>Card content text</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText('Card content text')).toBeInTheDocument();
  });

  it('should render CardFooter', () => {
    render(
      <Card>
        <CardFooter>
          <button>Footer Button</button>
        </CardFooter>
      </Card>
    );
    expect(screen.getByRole('button', { name: /footer button/i })).toBeInTheDocument();
  });

  it('should apply custom className to Card', () => {
    const { container } = render(
      <Card className="custom-card">
        <div>Content</div>
      </Card>
    );
    const card = container.querySelector('.custom-card');
    expect(card).toBeInTheDocument();
  });
});
