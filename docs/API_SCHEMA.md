https://ai.google.dev/gemini-api/docs/video?hl=ko&example=dialogue#reference-images

# Veo-3.1-fast

```json
{
  "type": "object",
  "title": "Input",
  "required": [
    "prompt"
  ],
  "properties": {
    "seed": {
      "type": "integer",
      "title": "Seed",
      "x-order": 8,
      "nullable": true,
      "description": "Random seed. Omit for random generations"
    },
    "image": {
      "type": "string",
      "title": "Image",
      "format": "uri",
      "x-order": 3,
      "nullable": true,
      "description": "Input image to start generating from. Ideal images are 16:9 or 9:16 and 1280x720 or 720x1280, depending on the aspect ratio you choose."
    },
    "prompt": {
      "type": "string",
      "title": "Prompt",
      "x-order": 0,
      "description": "Text prompt for video generation"
    },
    "duration": {
      "enum": [
        4,
        6,
        8
      ],
      "type": "integer",
      "title": "duration",
      "description": "Video duration in seconds",
      "default": 8,
      "x-order": 2
    },
    "last_frame": {
      "type": "string",
      "title": "Last Frame",
      "format": "uri",
      "x-order": 4,
      "nullable": true,
      "description": "Ending image for interpolation. When provided with an input image, creates a transition between the two images."
    },
    "resolution": {
      "enum": [
        "720p",
        "1080p"
      ],
      "type": "string",
      "title": "resolution",
      "description": "Resolution of the generated video",
      "default": "1080p",
      "x-order": 6
    },
    "aspect_ratio": {
      "enum": [
        "16:9",
        "9:16"
      ],
      "type": "string",
      "title": "aspect_ratio",
      "description": "Video aspect ratio",
      "default": "16:9",
      "x-order": 1
    },
    "generate_audio": {
      "type": "boolean",
      "title": "Generate Audio",
      "default": true,
      "x-order": 7,
      "description": "Generate audio with the video"
    },
    "negative_prompt": {
      "type": "string",
      "title": "Negative Prompt",
      "x-order": 5,
      "nullable": true,
      "description": "Description of what to exclude from the generated video"
    }
  }
}
```

# Veo-3.1

```json
{
  "type": "object",
  "title": "Input",
  "required": [
    "prompt"
  ],
  "properties": {
    "seed": {
      "type": "integer",
      "title": "Seed",
      "x-order": 9,
      "nullable": true,
      "description": "Random seed. Omit for random generations"
    },
    "image": {
      "type": "string",
      "title": "Image",
      "format": "uri",
      "x-order": 3,
      "nullable": true,
      "description": "Input image to start generating from. Ideal images are 16:9 or 9:16 and 1280x720 or 720x1280, depending on the aspect ratio you choose."
    },
    "prompt": {
      "type": "string",
      "title": "Prompt",
      "x-order": 0,
      "description": "Text prompt for video generation"
    },
    "duration": {
      "enum": [
        4,
        6,
        8
      ],
      "type": "integer",
      "title": "duration",
      "description": "Video duration in seconds",
      "default": 8,
      "x-order": 2
    },
    "last_frame": {
      "type": "string",
      "title": "Last Frame",
      "format": "uri",
      "x-order": 4,
      "nullable": true,
      "description": "Ending image for interpolation. When provided with an input image, creates a transition between the two images."
    },
    "resolution": {
      "enum": [
        "720p",
        "1080p"
      ],
      "type": "string",
      "title": "resolution",
      "description": "Resolution of the generated video",
      "default": "1080p",
      "x-order": 7
    },
    "aspect_ratio": {
      "enum": [
        "16:9",
        "9:16"
      ],
      "type": "string",
      "title": "aspect_ratio",
      "description": "Video aspect ratio",
      "default": "16:9",
      "x-order": 1
    },
    "generate_audio": {
      "type": "boolean",
      "title": "Generate Audio",
      "default": true,
      "x-order": 8,
      "description": "Generate audio with the video"
    },
    "negative_prompt": {
      "type": "string",
      "title": "Negative Prompt",
      "x-order": 6,
      "nullable": true,
      "description": "Description of what to exclude from the generated video"
    },
    "reference_images": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uri"
      },
      "title": "Reference Images",
      "default": [],
      "x-order": 5,
      "description": "1 to 3 reference images for subject-consistent generation (reference-to-video, or R2V). Reference images only work with 16:9 aspect ratio and 8-second duration. Last frame is ignored if reference images are provided."
    }
  }
}
```

# Nano banana (Gemini 2.5 flash image)
```json
{
  "type": "object",
  "title": "Input",
  "required": [
    "prompt"
  ],
  "properties": {
    "prompt": {
      "type": "string",
      "title": "Prompt",
      "x-order": 0,
      "description": "A text description of the image you want to generate"
    },
    "image_input": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uri"
      },
      "title": "Image Input",
      "default": [],
      "x-order": 1,
      "description": "Input images to transform or use as reference (supports multiple images)"
    },
    "aspect_ratio": {
      "enum": [
        "match_input_image",
        "1:1",
        "2:3",
        "3:2",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "9:16",
        "16:9",
        "21:9"
      ],
      "type": "string",
      "title": "aspect_ratio",
      "description": "Aspect ratio of the generated image",
      "default": "match_input_image",
      "x-order": 2
    },
    "output_format": {
      "enum": [
        "jpg",
        "png"
      ],
      "type": "string",
      "title": "output_format",
      "description": "Format of the output image",
      "default": "jpg",
      "x-order": 3
    }
  }
}
```