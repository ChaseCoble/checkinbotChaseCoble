API endpoints

GET /api/v1/posts/{post_id}/comments: Lists a posts's comment: 
	[
  {
    "id": 0,
    "body": "string",
    "post_id": 0,
    "author_id": 0,
    "author_name": "string",
    "created_at": "2026-09-13T20:00:29.380Z"
  }
]

POST /api/v1/posts/{post_id}/comments
{
  "body": "string"
}

GET /api/v1/posts: Get all posts

Params:
mine: boolean
author: integer (filter by id)
tag: (Filter by tag)
limit integer (1-100)
offset integer (0)

Response for GET /api/v1/posts/{post_id}
200	

Successful Response
Media type
Controls Accept header.

{
  "id": 0,
  "title": "string",
  "body": "string",
  "tags": [
    "string"
  ],
  "author_id": 0,
  "author_name": "string",
  "created_at": "2026-09-13T20:28:47.720Z",
  "updated_at": "2026-09-13T20:28:47.720Z",
  "attachments": [
    {
      "id": 0,
      "post_id": 0,
      "filename": "string",
      "content_type": "string",
      "size": 0,
      "download_url": "string",
      "created_at": "2026-09-13T20:28:47.720Z"
    }
  ]
}


ATTACHMENTS

GET
/api/v1/posts/{post_id}/attachments
List a post's attachments


[
  {
    "id": 0,
    "post_id": 0,
    "filename": "string",
    "content_type": "string",
    "size": 0,
    "download_url": "string",
    "created_at": "2026-09-13T20:30:28.079Z"
  }
]

GET
/api/v1/attachments/{attachment_id}
Download an attachment

'https://practice.fhsucyber.com/api/v1/attachments/0'

"string"
